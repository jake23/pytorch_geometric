import os
import os.path as osp
import glob

import torch
from torch_geometric.data import InMemoryDataset, download_url, extract_zip
from torch_geometric.read import read_off, read_txt_array


class SHREC2016(InMemoryDataset):
    r"""The SHREC 2016 partial matching dataset from the `"SHREC'16: Partial
    Matching of Deformable Shapes"
    <http://www.dais.unive.it/~shrec2016/shrec16-partial.pdf>`_ paper.

    .. note::

        Data objects hold mesh faces instead of edge indices.
        To convert the mesh to a graph, use the
        :obj:`torch_geometric.transforms.FaceToEdge` as :obj:`pre_transform`.
        To convert the mesh to a point cloud, use the
        :obj:`torch_geometric.transforms.SamplePoints` as :obj:`transform` to
        sample a fixed number of points on the mesh faces according to their
        face area.

    Args:
        root (string): Root directory where the dataset should be saved.
        partiality (string): The partiality of the dataset (one of
            :obj:`"Holes"`, :obj:`"Cuts"`)
        category (string): The category of the dataset (one of
            :obj:`"Cat"`, :obj:`"Centaur"`, :obj:`"David"`, :obj:`"Dog"`,
            :obj:`"Horse"`, :obj:`"Michael"`, :obj:`"Victoria"`,
            :obj:`"Wolf"`).
        train (bool, optional): If :obj:`True`, loads the training dataset,
            otherwise the test dataset. (default: :obj:`True`)
        transform (callable, optional): A function/transform that takes in an
            :obj:`torch_geometric.data.Data` object and returns a transformed
            version. The data object will be transformed before every access.
            (default: :obj:`None`)
        pre_transform (callable, optional): A function/transform that takes in
            an :obj:`torch_geometric.data.Data` object and returns a
            transformed version. The data object will be transformed before
            being saved to disk. (default: :obj:`None`)
        pre_filter (callable, optional): A function that takes in an
            :obj:`torch_geometric.data.Data` object and returns a boolean
            value, indicating whether the data object should be included in the
            final dataset. (default: :obj:`None`)
    """

    train_url = ('http://www.dais.unive.it/~shrec2016/data/'
                 'shrec2016_PartialDeformableShapes.zip')
    test_url = ('http://www.dais.unive.it/~shrec2016/data/'
                'shrec2016_PartialDeformableShapes_TestSet.zip')

    categories = [
        'cat', 'centaur', 'david', 'dog', 'horse', 'michael', 'victoria',
        'wolf'
    ]
    partialities = ['holes', 'cuts']

    def __init__(self,
                 root,
                 partiality,
                 category,
                 train=True,
                 transform=None,
                 pre_transform=None,
                 pre_filter=None):
        assert partiality.lower() in self.partialities
        self.part = partiality
        assert category.lower() in self.categories
        self.cat = category.lower()
        super(SHREC2016, self).__init__(root, transform, pre_transform,
                                        pre_filter)
        self.ref = torch.load(self.processed_paths[0])
        path = self.processed_paths[1] if train else self.processed_paths[2]
        self.data, self.slices = torch.load(path)

    @property
    def raw_file_names(self):
        return ['training', 'test']

    @property
    def processed_file_names(self):
        name = '{}_{}.pt'.format(self.part, self.cat)
        return ['{}_{}'.format(i, name) for i in ['ref', 'training', 'test']]

    def download(self):
        path = download_url(self.train_url, self.raw_dir)
        extract_zip(path, self.raw_dir)
        os.unlink(path)
        path = osp.join(self.raw_dir, 'shrec2016_PartialDeformableShapes')
        os.rename(path, osp.join(self.raw_dir, 'training'))

        path = download_url(self.test_url, self.raw_dir)
        extract_zip(path, self.raw_dir)
        os.unlink(path)
        path = osp.join(self.raw_dir,
                        'shrec2016_PartialDeformableShapes_TestSet')
        os.rename(path, osp.join(self.raw_dir, 'test'))

    def process(self):
        ref_data = read_off(
            osp.join(self.raw_paths[0], 'null', '{}.off'.format(self.cat)))

        trai_data_list = []
        name = '{}_{}_*.off'.format(self.part, self.cat)
        paths = glob.glob(osp.join(self.raw_paths[0], self.part, name))
        for i in range(1, len(paths) + 1):
            path = osp.join(self.raw_paths[0], self.part,
                            '{}_{}_shape_{}'.format(self.part, self.cat, i))
            data = read_off('{}.off'.format(path))
            y = read_txt_array('{}.baryc_gt'.format(path))
            data.y_idx = y[:, 0].to(torch.long)
            data.y_baryc = y[:, 1:]
            trai_data_list.append(data)

        test_data_list = []
        name = '{}_{}_*.off'.format(self.part, self.cat)
        paths = glob.glob(osp.join(self.raw_paths[1], self.part, name))
        for i in range(1, len(paths) + 1):
            path = osp.join(self.raw_paths[1], self.part,
                            '{}_{}_shape_{}'.format(self.part, self.cat, i))
            test_data_list.append(read_off('{}.off'.format(path)))

        if self.pre_filter is not None:
            trai_data_list = [d for d in trai_data_list if self.pre_filter(d)]
            test_data_list = [d for d in test_data_list if self.pre_filter(d)]

        if self.pre_transform is not None:
            ref_data = self.pre_transform(ref_data)
            trai_data_list = [self.pre_transform(d) for d in trai_data_list]
            test_data_list = [self.pre_transform(d) for d in test_data_list]

        torch.save(ref_data, self.processed_paths[0])
        torch.save(self.collate(trai_data_list), self.processed_paths[1])
        torch.save(self.collate(test_data_list), self.processed_paths[2])

    def __repr__(self):
        return '{}({}, partiality={}, category={})'.format(
            self.__class__.__name__, len(self), self.part, self.cat)
