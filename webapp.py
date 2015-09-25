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

THEMES_DIR            = '/home/zoni/project/brast-fire/themes'
STYLESHEET_PATH       = '/home/zoni/project/brast-fire/stylesheet.cs'
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
        return '\n'.join(['<!DOCTYPE html>'
                        '<html>',
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
        self.text   = theme_name

    def savePath(self):
        return os.path.join(THEMES_DIR, conv_encoding(self.text,'shift_jis'))

    def getIdeaList(self):
        assert os.path.exists(self.savePath()) , 'Theme:%s is not found.' % self.text
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
        self.text      = []
        self.note      = []
        self.pos       = (None, None)

    def path(self):
        return os.path.join(self.theme_dir, self.id)

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
            html.writeTag('a', 'アイデア:%s%s' % (conv_encoding(idea.text[0]), '...' if len(idea.text) > 1 else '')
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

    idea_name   = '\n'.join([conv_encoding(line) for line in idea.text]) if idea != None else ''
    description = '\n'.join([conv_encoding(line) for line in idea.note]) if idea != None else ''

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

    for l in idea.text:
        html.writeTag('p', conv_encoding(l))

    html.writeTag('h3', '補足')
    for l in idea.note:
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
        for l in idea.text:
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
    idea.text = [conv_encoding(l) for l in request.form['name'].split('\n')]
    idea.note = [conv_encoding(l) for l in request.form['memo'].split('\n')]
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
# Draggable Test (like Kanban)
#============================================================

def _renderingJScript(html):
    html.writeOpenTag('script', {'type':"text/javascript"})
    html.writeText('''
function onDragStart(event) {
  event.dataTransfer.setData("text", event.target.id);
}

function onDragOver(event) {
  event.preventDefault();
}

function onDrop(event) {
  var id_name  = event.dataTransfer.getData("text");
  var drag_elm = document.getElementById(id_name);
  event.currentTarget.appendChild(drag_elm);

  event.preventDefault();
}''')
    html.writeCloseTag('script')


def _renderingPostIt(html, theme_name, idea):
    html.writeOpenTag('div', {'class':'postit'
                              , 'draggable':'true'
                              , 'ondragstart':'onDragStart(event);'
                              , 'id': 'idea-%s' % idea.id})

    #title-bar
    html.writeOpenTag('div', {'class': 'postit-handle'})
    html.writeTag('a', '■',{'href': url_for('idea', theme=theme_name, idea_id=idea.id)})
    html.writeTag('span', '#%s' % idea.id)
    html.writeCloseTag('div')

    #body
    html.writeOpenTag('div', {'class': 'postit-face'})
    for l in idea.text:
        html.writeTag( 'p', conv_encoding(l))
    html.writeCloseTag('div')

    html.writeCloseTag('div')

def _renderingKanbanBoard(html, rownum, colnum, theme_name, idea_list):
    html.writeOpenTag('table', {'class':'board'})
    for row in range(0, rownum):
        html.writeOpenTag('tr', {'class':'board-row'})
        for col in range(0, colnum):
            html.writeOpenTag('td',{ 'class':'board-cell'
                                     ,'ondragover':'onDragOver(event);'
                                     ,'ondrop'    :'onDrop(event);'
                                     ,'id' :'bcell%d_%d' % (col,row)})
            for idea in [i for i in idea_list if (i.pos[0] == row and i.pos[1] == col)]:
                _renderingPostIt(html, theme_name, idea)
            html.writeCloseTag('td')
        html.writeCloseTag('tr')
    html.writeCloseTag('table')

def _calcGridSize(rowmin, colmin, idea_list):
    try:
        rowmax = max([i.pos[1] for i in idea_list if i.pos[1] != None])
        colmax = max([i.pos[0] for i in idea_list if i.pos[0] != None])

        return (colmax if colmin < colmax else colmin,
                rowmax if rowmin < rowmax else rowmin)

    except ValueError:
        return (rowmin, colmin)

@app.route("/test/<theme_name>")
def test(theme_name):
    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, theme_name)
    _renderingJScript(html, theme_name)

    theme = BTTheme(conv_encoding(theme_name))
    idea_list = theme.getIdeaList()
    colnum , rownum = _calcGridSize(2, 3, idea_list)

    _renderingKanbanBoard(html, rownum, colnum, theme_name, idea_list)

    html.writeOpenTag('div')
    html.writeTag('p', '*未配置*')
    for idea in (i for i in idea_list if i.pos[0] == None and i.pos[1] == None):
        _renderingPostIt(html,theme_name,idea)
    html.writeCloseTag('div')


    html.writeTag('a', 'アイデアを追加', {'href': url_for('add_new_idea', theme=theme_name)})

    return html.rendering()

#============================================================
# The application main (for Debug)
#============================================================

if __name__ == '__main__':
    app.debug = True
    app.run(port=5050)

