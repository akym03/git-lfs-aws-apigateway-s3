from abc import ABCMeta, abstractclassmethod


class Datastore(metaclass=ABCMeta):

    @abstractclassmethod
    def get_upload_url(self, key):
        pass

    @abstractclassmethod
    def get_download_url(self, key):
        pass

    @abstractclassmethod
    def get_info(self, key):
        pass

    @abstractclassmethod
    def exists(self, key, invert=False):
        pass
