import sys
sys.path.append('../../')
# sys.path.append('../Drivers/')# 增加驱动搜索目录

from speedTornado.config import Config
from speedTornado.Core.Model import Model

class User(Model):

    # 表名
    tbl_name = 'users'


    def __init__(self):
        super(eval(self.__class__.__name__), self).__init__()
