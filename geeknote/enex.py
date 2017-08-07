import codecs
import os
import re
import locale
from time import gmtime,strftime 
import base64

import lxml.etree as ET
from lxml.etree import SubElement
# import xml.etree.ElementTree as ET
# from xml.etree.ElementTree import SubElement

from xml.sax.saxutils import escape, unescape

import config
from geeknote import GeekNote
from gnsync import GNSync

os_encoding = locale.getpreferredencoding()
user_info = GeekNote().getUserInfo()

def log(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            print e
            traceback.print_exc()
            logger.error("%s", str(e))
    return wrapper

def _list_member(obj):
    for attr_name, attr in obj.__dict__.items():    
        print (attr_name, type(attr), attr)

def get_info_from_file( path ):
    tree = None  
    if os.path.isfile(path):
        print ("get info from local file {}".format(path))
        try:
            tree = ET.parse(path)
        except:
            print ("fail")
            return 
                   
    server_elm = tree.find("server_info")
    title = tree.find('note/title').text
    mtime = int(os.path.getmtime(path) * 1000)
    note_ids = []
    if server_elm is not None:
        for id in server_elm.iter("note_id"):
            note_ids.append(id.text)        
    print note_ids
    return {'path': path, 'name': title.encode(os_encoding), 'mtime': mtime, 'note_id':note_ids}
    
def note_to_file(note, path):
    old_tree = None  
    if os.path.isfile(path):
        print ("parse file {}".format(path))
        try:
            old_tree = ET.parse(path)
        except:
            print ("fail")                        
    enex_file = open( path, "wb+")
    enex_file.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE en-export PUBLIC "SYSTEM" "http://xml.evernote.com/pub/evernote-export3.dtd">\n')
    export_elm = ET.Element('en-export')
    tree = ET.ElementTree(export_elm)        
    note_elm = SubElement(export_elm, 'note')
    title_elm = SubElement(note_elm, 'title')
    title_elm.text = note.title.decode('utf-8')
    content_elm = SubElement(note_elm, "content")
    print_title = title_elm.text.encode(os_encoding)
    content_elm.text = ET.CDATA(note.content.decode('utf-8'))
    SubElement(note_elm, 'created').text = strftime("%Y%m%dT%H%M%SZ", gmtime(note.created / 1000))
    SubElement(note_elm, 'updated').text = strftime("%Y%m%dT%H%M%SZ", gmtime(note.updated / 1000))
    
    if (note.tagGuids):
        for tag in note.tagNames:
            SubElement(note_elm, 'tag').text = tag
            
    note_attr_elm = SubElement(note_elm, 'note-attributes')

    upper_regex = re.compile("[A-Z]")
    first_cap_re = re.compile('(.)([A-Z][a-z]+)')
    all_cap_re = re.compile('([a-z0-9])([A-Z])')
    def _conv_export_name(name):
        s1 = first_cap_re.sub(r'\1_\2', name)
        return all_cap_re.sub(r'\1_\2', s1).lower()
                
    for attr_name, attr in note.attributes.__dict__.items():
#         print (attr_name, type(attr), attr)
        if attr != None:
            attr_name = _conv_export_name(attr_name)
            if isinstance(attr, basestring):
                SubElement(note_attr_elm, attr_name).text = attr.decode("utf-8")
            if isinstance(attr, long):
                if ('time' in attr_name or 'date' in attr_name):
                    SubElement(note_attr_elm, attr_name).text = strftime("%Y%m%dT%H%M%SZ", gmtime(attr / 1000))
                else:
                    SubElement(note_attr_elm, attr_name).text = str(attr)     
            if isinstance(attr, (float, bool)):
                SubElement(note_attr_elm, attr_name).text = str(attr)   
                     
    if (note.largestResourceSize) is not None:
        print ("largest resource size of {} = {} ".format(print_title, note.largestResourceSize))
        note_obj = GeekNote().getNote(note.guid, withResourcesData=True, withResourcesRecognition=True)
        for res in note_obj.resources:
            res_elm = SubElement(note_elm, 'resource')
            print ("found resource with size {} in {} ".format(res.data.size, print_title))
            SubElement(res_elm, 'data', encoding="base64").text = str(base64.b64encode(res.data.body))
            SubElement(res_elm, 'mime').text = res.mime
            if res.width != None: SubElement(res_elm, 'width').text = str(res.width)                 
            if res.height != None:SubElement(res_elm, 'height').text = str(res.height)
            if res.recognition != None:SubElement(res_elm, 'recognition').text = ET.CDATA(res.recognition.body.decode("utf-8")) 
            res_attr_elm = SubElement(res_elm, 'resource-attributes')
                               
            for attr_name, attr in res.attributes.__dict__.items():
                if attr == None:
                    continue
                attr_name = _conv_export_name(attr_name)
                if isinstance(attr, basestring):
                    attr = attr.decode("utf-8")
                    SubElement(res_attr_elm, attr_name).text = attr
                if ('time' in attr_name or 'date' in attr_name):
                    SubElement(res_attr_elm, attr_name).text = strftime("%Y%m%dT%H%M%SZ", gmtime(attr / 1000))
                if isinstance(attr, (float, bool)):
                    SubElement(res_attr_elm, attr_name).text = str(attr)
   
    if (old_tree != None):
        prst_servers_info = old_tree.find("server_info")
        if prst_servers_info is not None:
            for account in prst_servers_info:
                if account.find("note_id").text == note.guid:
                    print ("Remove old server info")
#                     prst_servers_info.remove(account)
                

#             print (server.find("base_site")) 
#             print ("note stored in {} with account {}".format(server.find("base_site").text,(server.find("account").text)))        
#     _list_member(user_info)
    server_elm = SubElement(export_elm, 'server_info')
    account_elm = SubElement(server_elm, 'account')
    SubElement(account_elm, "note_id").text = note.guid
    SubElement(account_elm, "notebook_name").text = note.notebookName
    SubElement(account_elm, "user_id").text = str(user_info.id)
    SubElement(account_elm, "user_full_name").text = user_info.name.decode("utf-8")
    SubElement(account_elm, "base_site").text = config.USER_BASE_URL
    SubElement(account_elm, "last_update").text = str(note.updated)
                        
    enex_file.write(unescape(ET.tostring(export_elm, encoding='utf-8', pretty_print=True)))
    enex_file.truncate()
    return True
