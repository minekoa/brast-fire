#-*- coding: utf-8 -*-

from flask import Flask, redirect, url_for, request, abort, Response
import xml.sax.saxutils
import os
import os.path
import datetime
import re
import sys

#============================================================
# Config
#============================================================

THEMES_DIR            = 'F:/zhome/webbin/brastfire/themes'
STYLESHEET_PATH       = 'F:/zhome/webbin/brastfire/stylesheet.cs'
THEME_IDEA_COL_NUMBER = 3

#============================================================
# Tool
#============================================================

def conv_encoding(data, to_enc="utf_8"):
    """
    stringのエンコーディングを変換する
    @param ``data'' str object.
    @param ``to_enc'' specified convert encoding.
    @return str object.
    @note http://speirs.blog17.fc2.com/blog-entry-4.html より
    """
    lookup = ('utf_8', 'euc_jp', 'euc_jis_2004', 'euc_jisx0213',
            'shift_jis', 'shift_jis_2004','shift_jisx0213',
            'iso2022jp', 'iso2022_jp_1', 'iso2022_jp_2', 'iso2022_jp_3',
            'iso2022_jp_ext','latin_1', 'ascii')
    for encoding in lookup:
        try:
            data = data.decode(encoding)
            break
        except:
            pass
    if isinstance(data, unicode):
        return data.encode(to_enc)
    else:
        return data


def create_new_idea_id():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S") 


#============================================================
# Html Rendering (Framework)
#============================================================

class HtmlCanvasBase(object):
    '''Base Class for HtmlHeaderCanvas and HtmlCanvas(=body+header)'''
    def __init__(self):
        self.buf = ''

    def _write(self, text):
        self.buf += conv_encoding(text)

    def _html_escape(self, aStr):
        return xml.sax.saxutils.escape(aStr)

    def _attr_escape(self, aStr):
        return xml.sax.saxutils.quoteattr(aStr)

    def writeOpenTag(self, tag_name, attr_list={}):
        self._write('<%s' % tag_name)
        for key, value in attr_list.items():
            self._write(' %s=%s' % (key, self._attr_escape(value)))
        self._write('>')

    def writeCloseTag(self, tag_name):
        self._write('</%s>' % tag_name)

    def writeText(self, text):
        self._write(self._html_escape(text))

    def writeRawText(self, text):
        self._write(text)

    def writeTag(self, tag_name, text, attr_list={}):
        self.writeOpenTag(tag_name, attr_list)
        self.writeText(text)
        self.writeCloseTag(tag_name)

class HtmlHeaderCanvas(HtmlCanvasBase):
    """todo: <head> 's attribute writer"""
    pass

class HtmlCanvas(HtmlCanvasBase):
    """todo: <body> 's attribute writer"""
    def __init__(self):
        HtmlCanvasBase.__init__(self)    # html body
        self.header = HtmlHeaderCanvas() # html header

    def rendering(self):
        return ''.join(['<html>',
                        '<head>', self.header.buf, '</head>'
                        '<body>', self.buf, '</body>'
                        '</html>'])


#============================================================
# Model (Theme & issue)
#============================================================

class BTTheme(object):
    '''
    todo: テーマの Wiki (description.txt とかを読みこませるか？)
    '''
    def __init__(self, theme_name):
        self.name   = theme_name

    def savePath(self):
        return os.path.join(THEMES_DIR, conv_encoding(self.name,'shift_jis'))

    def getIdeaList(self):
        assert os.path.exists(self.savePath()) , 'Theme:%s is not found.' % self.name
        idea_list = []

        for dpath, dirs, files in os.walk(self.savePath()):
            files.sort()
            
            for fpath in files:
                if re.match(r"^[0-9]+_[0-9]+$", fpath) == None: continue
                idea = BTIdea(dpath, fpath)
                idea.load()
                idea_list.append(idea)
        return idea_list

    def saveThemeInfo(self):
        if not os.path.exists(self.savePath()):
            os.mkdir(self.savePath())

class BTIdea(object):
    def __init__(self, dpath, idea_id):
        self.theme_dir = dpath
        self.id        = idea_id
        self.name      = []
        self.memo      = []

    def sepline(self):
        return "================\n"

    def path(self):
        return os.path.join(self.theme_dir, self.id)

    def load(self):
        f = open(self.path(),'r')

        memo_reading = False
        for line in f.readlines():
            if not memo_reading:
                if line.strip() == self.sepline().strip():
                    memo_reading = True
                    continue
                self.name.append( "%s" % line.strip() )

            else:
                self.memo.append(line.strip())
        f.close()

    def save(self):
        f = open(self.path(),'w')
        f.write('\n'.join(line.strip() for line in self.name))
        f.write('\n')
        f.write(self.sepline())
        f.write('\n'.join(line.strip() for line in self.memo))
        f.close()

#============================================================
# View - elaborate global objects
#============================================================

app = Flask(__name__)


#============================================================
# View - common rendering functions
#============================================================

def renderingHtmlHeader(canvas):
    canvas.header.writeTag('meta', '', {'HTTP-EQUIV':'Content-Style-Type', 'content':'text/css'})
    canvas.header.writeTag('link', '', {'rel':'stylesheet', 'href':url_for('static', filename='stylesheet.css'), 'type':'text/css'})

def renderingPageHeader(html,theme_name='', idea=None):
    html.writeTag('h1', 'BRAST-FIRE!')
    if theme_name != '':
        html.writeOpenTag('div', {'class':'navibar'})
        html.writeTag('a', 'お題:%s' % conv_encoding(theme_name), {'href': url_for('theme', theme_name=theme_name)})

        if idea != None:
            html.writeText('>>')
            html.writeTag('a', 'アイデア:%s%s' % (conv_encoding(idea.name[0]), '...' if len(idea.name) > 1 else '')
                          , {'href': url_for('idea', theme=theme_name, idea_id=idea.id)})
            html.writeText('[')
            html.writeTag('a', '編集' , {'href': url_for('edit_idea', theme=theme_name, idea_id=idea.id)})
            html.writeText(']')

        html.writeCloseTag('div')

def renderingItemForm(html, post_url, idea=None):
    '''
    入力ガイドは以下のサイトを参考にした
    http://www.ritsumei.ac.jp/~yamai/kj.htm
    '''
    html.writeOpenTag('form', {'method':'post', 'action': post_url})

    idea_name   = '\n'.join([conv_encoding(line) for line in idea.name]) if idea != None else ''
    description = '\n'.join([conv_encoding(line) for line in idea.memo]) if idea != None else ''

    html.writeOpenTag('div')
    html.writeTag('h3', 'Idea(一行見出し):')
    html.writeTag('textarea', idea_name, {'name':'name'})
    html.writeTag('p', conv_encoding("一行見出し: 簡潔かつ内容を正確に表現する（実際には２・３行になってもよい）。あまり長すぎぬよう（20～30字以内）にすること。できるだけソフトで、かつ本質をしっかりとらえた表現にすること。"))
    html.writeCloseTag('div')

    html.writeOpenTag('div')
    html.writeTag('h3', 'Note:')
    html.writeTag('textarea', description, {'name':'memo'})
    html.writeTag('p', conv_encoding("※オプション（書かなくても良い）。発言者・発言時間などをとっておきたければ記載する"))
    html.writeCloseTag('div')

    html.writeOpenTag('div')
    html.writeOpenTag('input', {'type':'submit', 'value':'Accept'})
    html.writeCloseTag('div')
    html.writeCloseTag('form')

def renderingIdea(html, idea):
    html.writeTag('h3', '一行見出し')

    for l in idea.name:
        html.writeTag('p', conv_encoding(l))

    html.writeTag('h3', '補足')
    for l in idea.memo:
        html.writeTag('p', conv_encoding(l))

#============================================================
# View - page functions (entry points)
#============================================================

@app.route("/")
def index():
    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html)
    html.writeOpenTag('p')
    html.writeTag('a', '新しいテーマを作成する', {'href': url_for('add_new_theme')})
    html.writeCloseTag('p')

    html.writeOpenTag('ul')
    for dpath, dirs, files in os.walk(THEMES_DIR):
        for dir in dirs:
            html.writeOpenTag('li')
            html.writeTag('a', conv_encoding(dir), {'href': url_for('theme', theme_name=conv_encoding(dir))})
            html.writeCloseTag('li')
    html.writeCloseTag('ul')

    return html.rendering()

@app.route("/theme/<theme_name>")
def theme(theme_name):
    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, theme_name)

    theme = BTTheme(conv_encoding(theme_name))
    html.writeOpenTag('table')
    html.writeOpenTag('tr')
    html.writeTag('th', 'アイデアボード', {'colspan': '%d' % THEME_IDEA_COL_NUMBER})
    html.writeCloseTag('tr')

    col_cnt = 0
    html.writeOpenTag('tr')

    for idea in theme.getIdeaList():
        if col_cnt == THEME_IDEA_COL_NUMBER:
            html.writeCloseTag('tr')
            html.writeOpenTag('tr')
            col_cnt = 0
            
        html.writeOpenTag('td')
        html.writeOpenTag('a',{'href': url_for('idea', theme=theme_name, idea_id=idea.id)})
        for l in idea.name:
            html.writeTag( 'p', conv_encoding(l))
        html.writeCloseTag('a')

        col_cnt += 1

    html.writeCloseTag('tr')
    html.writeCloseTag('table')

    html.writeTag('a', 'アイデアを追加', {'href': url_for('add_new_idea', theme=theme_name)})

    return html.rendering()

@app.route("/add_new_theme/")
def add_new_theme():
    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html)

    html.writeOpenTag('form', {'method':'post',
                               'action': url_for('save_theme')})
    html.writeOpenTag('div')
    html.writeTag('h3', 'Idea Name:')
    html.writeTag('textarea', '', {'name':'name'})
    html.writeCloseTag('div')

    html.writeOpenTag('div')
    html.writeOpenTag('input', {'type':'submit', 'value':'Accept'})
    html.writeCloseTag('div')
    html.writeCloseTag('form')

    return html.rendering()

@app.route("/save_theme/", methods=['POST'])
def save_theme():
    theme = BTTheme(conv_encoding(request.form['name']))
    theme.saveThemeInfo()

    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, conv_encoding(request.form['name']))

    return html.rendering()

@app.route("/add_new_idea/<theme>")
def add_new_idea(theme):
    idea_id = create_new_idea_id()

    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, theme)

    renderingItemForm(html, url_for('save_idea', theme=theme, idea_id=idea_id))
    return html.rendering()

@app.route("/edit_idea/<theme>/<idea_id>")
def edit_idea(theme, idea_id):
    idea = BTIdea(os.path.join(THEMES_DIR, theme), idea_id)
    idea.load()

    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, theme)

    renderingItemForm(html, url_for('save_idea', theme=theme, idea_id=idea_id), idea)

    return html.rendering()

@app.route("/save_idea/<theme>/<idea_id>", methods=['POST'])
def save_idea(theme, idea_id):
    idea = BTIdea(os.path.join(THEMES_DIR, theme), idea_id)
    idea.name = [conv_encoding(l) for l in request.form['name'].split('\n')]
    idea.memo = [conv_encoding(l) for l in request.form['memo'].split('\n')]
    idea.save()

    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, theme, idea)
    html.writeTag('p', conv_encoding('セーブしました'))

    # ロードして読めるか確認
    idea = BTIdea(os.path.join(THEMES_DIR, theme), idea_id)
    idea.load()
    renderingIdea(html, idea)
    return html.rendering()

@app.route("/idea/<theme>/<idea_id>")
def idea(theme, idea_id):
    idea = BTIdea(os.path.join(THEMES_DIR, theme), idea_id)
    idea.load()

    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, theme, idea)
    renderingIdea(html, idea)
    return html.rendering()


#============================================================
# The application main (for Debug)
#============================================================

if __name__ == '__main__':
    app.debug = True
    app.run(port=5050)
