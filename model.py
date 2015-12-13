#-*- coding: utf-8 -*-

import os
import os.path
import re
import sys

from config import *
from common import *

#============================================================
# Model (Theme & issue)
#============================================================

class BTTheme(object):
    '''
    todo: テーマの Wiki (description.txt とかを読みこませるか？)
    '''
    def __init__(self, theme_name):
        self.text    = theme_name

        self.setting = BTThemeSetting(self.savePath())
        if self.setting.existSaveFile():
            self.setting.load()

    def savePath(self):
        return os.path.join(THEMES_DIR, conv_encoding(self.text,'shift_jis'))

    def getIdeaFileNames(self):
        files = [f for f in os.listdir(self.savePath()) 
                 if os.path.isfile(os.path.join(self.savePath(),f)) and re.match(r"^[0-9]+_[0-9]+$", f) != None]
        files.sort()
        return files

    def getIdeaCount(self):
        return len(self.getIdeaFileNames())

    def getIdeaList(self):
        assert os.path.exists(self.savePath()) , 'Theme:%s is not found.' % self.text
        idea_list = []
        for fpath in self.getIdeaFileNames():
            idea = BTIdea(self.savePath(), fpath)
            idea.load()
            idea_list.append(idea)
        return idea_list

    def saveThemeInfo(self):
        if not os.path.exists(self.savePath()):
            os.mkdir(self.savePath())
        self.setting.save()

    def colCount(self):
        fixedColSize = self.setting.fixedBoardSize[IdxOfCol]
        return fixedColSize if fixedColSize != None else self.calcColSize()

    def rowCount(self):
        fixedRowSize = self.setting.fixedBoardSize[IdxOfRow]
        return fixedRowSize if fixedRowSize != None else self.calcRowSize()

    def calcColSize(self):
        fixedRowSize = self.setting.fixedBoardSize[IdxOfRow]
        ideaCount    = self.getIdeaCount()
        if fixedRowSize != None:
            return ideaCount / fixedRowSize + (0 if ideaCount % fixedRowSize == 0 else 1)
        else:
            return DEFAULT_BOARD_COL_COUNT

    def calcRowSize(self):
        fixedColSize = self.setting.fixedBoardSize[0]
        ideaCount    = self.getIdeaCount()
        if fixedColSize == None:
            fixedColSize = DEFAULT_BOARD_COL_COUNT
        return ideaCount / fixedColSize + (0 if ideaCount % fixedColSize == 0 else 1)


class BTThemeSetting(object):
    def __init__(self, themeDirPath):
        '''
        make setting params fill default value
        '''
        self.themeDirPath   = themeDirPath

        # theme satting params
        self.fixedBoardSize = (None, None) # col, row

    def _saveFilePath(self):
        return os.path.join(self.themeDirPath, THEME_SETTING_FILE_NAME)

    def existSaveFile(self):
        return os.path.exists(self._saveFilePath())

    def load(self):
        with  open(self._saveFilePath(), 'r') as settingFile:
            for line in settingFile:
                exp_pair = line.split('=')
                if len(exp_pair) == 2:
                    setattr(self, exp_pair[0], eval(exp_pair[1]))

    def save(self):
        with  open(self._saveFilePath(), 'w') as settingFile:
            settingFile.write('fixedBoardSize=%s\n' % self.fixedBoardSize.__repr__())


class BTIdea(object):
    def __init__(self, dpath, idea_id):
        self.theme_dir = dpath
        self.id        = idea_id
        self.text      = []
        self.note      = []
        self.pos       = (None, None)

    def path(self):
        return os.path.join(self.theme_dir, self.id)

    def exists(self):
        return os.path.exists(self.path())

    def load(self):
        f = open(self.path(),'r')

        in_meta = True
        for line in f.readlines():
            # load meta info
            if in_meta:
               if line.strip() == '': in_meta = False
               else:
                   exp_pair = line.split('=')
                   if len(exp_pair) == 2:
                       setattr(self, exp_pair[0], eval(exp_pair[1]))
                   else:
                       in_meta = False
               continue
            
            # load text
            self.text.append( "%s" % line.strip() )

        f.close()

    def save(self):
        f = open(self.path(),'w')
        f.write('pos=%s\n' % self.pos.__repr__())
        f.write('note=%s\n' % self.note.__repr__())
        f.write('\n')
        f.write('\n'.join(line.strip() for line in self.text))
        f.write('\n')
        f.close()

