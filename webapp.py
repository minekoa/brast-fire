#-*- coding: utf-8 -*-

from flask import Flask, redirect, url_for, request, abort, Response
import xml.sax.saxutils
import os
import os.path
import datetime
import re
import sys

from common import * # tool and constants
from config import *

import model

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

@app.route("/add_new_theme/")
def add_new_theme():
    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html)

    html.writeOpenTag('form', {'method':'post',
                               'action': url_for('save_theme')})
    # edit Theme Name
    html.writeOpenTag('div')
    html.writeTag('h3', 'Idea Name:')
    html.writeTag('textarea', '', {'name':'name'})
    html.writeCloseTag('div')

    # edit Board Size
    html.writeOpenTag('div')
    html.writeTag('h3', 'Board Size (Optional)')
    html.writeTag('span', '(col, row) = (')
    html.writeTag('input', '', {'type':'text', 'name':'col', 'size':'3'})
    html.writeTag('span', ',')
    html.writeTag('input', '', {'type':'text', 'name':'row', 'size':'3'})
    html.writeTag('span', ')  ... if you required auto adjust, keep a blank text.')
    html.writeCloseTag('div')
    
    # Edit Column Header
    html.writeOpenTag('div')
    html.writeTag('h3', 'Column Header (Optional)')
    html.writeTag('p', 'カンマで区切って記述します。カンマを含むヘッダは諦めてね。')
    html.writeTag('input', '', {'type':'text', 'name':'column_header'})
    html.writeCloseTag('div')

    html.writeOpenTag('div')
    html.writeOpenTag('input', {'type':'submit', 'value':'Accept'})
    html.writeCloseTag('div')
    html.writeCloseTag('form')

    return html.rendering()

@app.route("/save_theme/", methods=['POST'])
def save_theme():
    theme = model.BTTheme(conv_encoding(request.form['name']))

    col = int(request.form['col']) if request.form['col'] != '' else None
    row = int(request.form['row']) if request.form['row'] != '' else None
    assert col == None or col > 0, 'invalid column count "%s"' % col
    assert row == None or row > 0, 'invalid row count "%s"' % row

    col_header = [header.strip() for header in request.form['column_header'].split(',')]
    assert len(col_header) == col, 'nomatch col_header_item_num <> column_num'

    theme.setting.fixedBoardSize = (col, row)
    theme.setting.columnHeader   = col_header
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
    idea = model.BTIdea(os.path.join(THEMES_DIR, theme), idea_id)
    idea.load()

    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, theme)

    renderingItemForm(html, url_for('save_idea', theme=theme, idea_id=idea_id), idea)

    return html.rendering()

@app.route("/save_idea/<theme>/<idea_id>", methods=['POST'])
def save_idea(theme, idea_id):
    idea = model.BTIdea(os.path.join(THEMES_DIR, theme), idea_id)
    if idea.exists():
        idea.load()
    idea.text = [conv_encoding(l) for l in request.form['name'].split('\n')]
    idea.note = [conv_encoding(l) for l in request.form['memo'].split('\n')]
    idea.save()

    return redirect(url_for('theme', theme_name=theme))

@app.route("/idea/<theme>/<idea_id>")
def idea(theme, idea_id):
    idea = model.BTIdea(os.path.join(THEMES_DIR, theme), idea_id)
    idea.load()

    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, theme, idea)
    renderingIdea(html, idea)
    return html.rendering()



#============================================================
# Draggable Test (like Kanban)
#============================================================

def _renderingJScript(html, theme_name):
    html.writeOpenTag('script', {'type':"text/javascript"})
    html.writeRawText('''
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

  notifyMovePostit(id_name, event.currentTarget.id);
  event.preventDefault();
}''')

    html.writeRawText('''
function notifyMovePostit(idea_id, bcell_id){
    var data = { idea: idea_id, bcell: bcell_id };

    var ajaxObject = new XMLHttpRequest();

    ajaxObject.onreadystatechange = function() {
        var READYSTATE_COMPLETED = 4;
        var HTTP_STATUS_OK = 200;
        if (this.readyState == READYSTATE_COMPLETED && this.status == HTTP_STATUS_OK) {
            /*alert( this.responseText );*/
        }
    };

    ajaxObject.open("POST", "%s", true);
    ajaxObject.setRequestHeader( 'Content-Type', 'application/x-www-form-urlencoded' );
    ajaxObject.send( 'idea=' + idea_id + '&bcell=' + bcell_id);
}''' % url_for('move_postit', theme=theme_name))


    html.writeCloseTag('script')


def _renderingPostIt(html, theme_name, idea):
    html.writeOpenTag('div', {'class':'postit'
                              , 'draggable':'true'
                              , 'ondragstart':'onDragStart(event);'
                              , 'id': 'idea-%s' % idea.id})

    # handle-bar
    html.writeOpenTag('div', {'class': 'postit_handle'})

    html.writeOpenTag('div', {'class': 'postit_handle_id'})
    html.writeTag('a', '■',{'href': url_for('idea', theme=theme_name, idea_id=idea.id)})
    html.writeText('#%s' % idea.id)
    html.writeCloseTag('div')

    html.writeOpenTag('div', {'class':'postit_handle_edit'})
    html.writeTag('a', '[edit]',{'href': url_for('edit_idea', theme=theme_name, idea_id=idea.id)})
    html.writeCloseTag('div')

    # handle-bar > popup-note
    html.writeOpenTag('div', {'class': 'popup_note'})
    for l in idea.note:  html.writeTag( 'p', conv_encoding(l))
    html.writeCloseTag('div')

    html.writeCloseTag('div') # close handle-bar

    #body
    html.writeOpenTag('div', {'class': 'postit_face'})
    for l in idea.text: html.writeTag( 'p', conv_encoding(l))
    html.writeCloseTag('div')

    html.writeCloseTag('div')

def _renderingKanbanBoard(html, colnum, rownum, theme_name, column_header, idea_list):
    html.writeOpenTag('table', {'class':'board'})

    # rendering table-header
    if len(column_header) != 0:
        html.writeOpenTag('tr')
        for header_string in column_header:
            html.writeTag('th', header_string)
        html.writeCloseTag('tr')

    # rendering table-body
    for row in range(0, rownum):
        html.writeOpenTag('tr', {'class':'board-row'})
        for col in range(0, colnum):
            html.writeOpenTag('td',{ 'class':'board-cell'
                                     ,'ondragover':'onDragOver(event);'
                                     ,'ondrop'    :'onDrop(event);'
                                     ,'id' :'bcell%d_%d' % (col,row)})
            for idea in [i for i in idea_list if (i.pos[IdxOfRow] == row and i.pos[IdxOfCol] == col)]:
                _renderingPostIt(html, theme_name, idea)
            html.writeCloseTag('td')
        html.writeCloseTag('tr')
    html.writeCloseTag('table')

def _calcGridSize(colmin, rowmin, idea_list):
    try:
        colmax = max([i.pos[IdxOfCol] for i in idea_list if i.pos[IdxOfCol] != None])
        rowmax = max([i.pos[IdxOfRow] for i in idea_list if i.pos[IdxOfRow] != None])

        return (colmax if colmin < colmax else colmin,
                rowmax if rowmin < rowmax else rowmin)
                

    except ValueError:
        return (colmin, rowmin)

@app.route("/theme/<theme_name>")
def theme(theme_name):
    html = HtmlCanvas()
    renderingHtmlHeader(html)
    renderingPageHeader(html, theme_name)
    _renderingJScript(html, theme_name)

    theme = model.BTTheme(conv_encoding(theme_name))
    idea_list = theme.getIdeaList()

    colnum , rownum = _calcGridSize(theme.colCount(), theme.rowCount(), idea_list)
    col_header      = theme.setting.columnHeader

    _renderingKanbanBoard(html, colnum, rownum, theme_name, col_header, idea_list)

    html.writeOpenTag('div')
    html.writeTag('p', '*未配置*')
    for idea in (i for i in idea_list if i.pos[0] == None and i.pos[1] == None):
        _renderingPostIt(html,theme_name,idea)
    for idea in (i for i in idea_list if i.pos[IdxOfCol] > colnum or i.pos[IdxOfRow] == rownum):
        _renderingPostIt(html,theme_name,idea)
    html.writeCloseTag('div')


    html.writeTag('a', 'アイデアを追加', {'href': url_for('add_new_idea', theme=theme_name)})

    return html.rendering()


@app.route("/move_postit/<theme>", methods=['POST'])
def move_postit(theme):

    matobj = re.match(r"idea-([0-9_]+)", request.form['idea'])
    idea_id = matobj.group(1)
    matobj = re.match(r"bcell([0-9]+)_([0-9]+)", request.form['bcell'])
    col = int(matobj.group(1))
    row = int(matobj.group(2))

    idea = model.BTIdea(os.path.join(THEMES_DIR, theme), idea_id)
    idea.load()
    idea.pos = (col, row)
    idea.save()

    return 'MOVE_SAVED! %s -to-> %s' % (request.form['idea'], request.form['bcell'])

#============================================================
# The application main (for Debug)
#============================================================

if __name__ == '__main__':
    app.debug = True
    app.run(port=5050)

