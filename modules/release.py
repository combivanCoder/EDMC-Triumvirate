
"""
Module to provide the news.
"""

import Tkinter as tk
from Tkinter import Frame
import uuid
from ttkHyperlinkLabel import HyperlinkLabel
import requests
import json
import re
import myNotebook as nb
from config import config
import zipfile
import StringIO
import os
import shutil
import threading
from  player import Player
from debug import Debug
from debug import debug,error

RELEASE_CYCLE=60 * 1000 * 60 # 1 Hour
DEFAULT_URL = 'https://github.com/VAKazakov/EDMC-Triumvirate/releases'
WRAP_LENGTH = 200

def _callback(matches):
    id = matches.group(1)
    try:
        return unichr(int(id))
    except:
        return id


def decode_unicode_references(data):
    return re.sub("&#(\d+)(;|(?=\s))", _callback, data)

class ReleaseLink(HyperlinkLabel):

    def __init__(self, parent):

        HyperlinkLabel.__init__(
            self,
            parent,
            text="Fetching...",
            url=DEFAULT_URL,
            wraplength=50,  # updated in __configure_event below
            anchor=tk.NW
        )
        self.bind('<Configure>', self.__configure_event)

    def __configure_event(self, event):
        "Handle resizing."

        self.configure(wraplength=event.width)
    
class ReleaseThread(threading.Thread):
    def __init__(self,release):
        threading.Thread.__init__(self)
        self.release=release
    
    def run(self):
        debug("Release: UpdateThread")
        self.release.release_pull()
        
        
class Release(Frame):

    def __init__(self, parent,release,gridrow):
        "Initialise the ``News``."

        padx, pady = 10, 5  # formatting
        sticky = tk.EW + tk.N  # full width, stuck to the top
        anchor = tk.NW        
        
        Frame.__init__(
            self,
            parent
        )
        
        self.auto=tk.IntVar(value=config.getint("AutoUpdate"))                
        self.novoices=tk.IntVar(value=config.getint("NoVoices"))                
        self.rmbackup=tk.IntVar(value=config.getint("RemoveBackup"))                
        
        self.columnconfigure(1, weight=1)
        self.grid(row = gridrow, column = 0, sticky="NSEW",columnspan=2)
        
        self.label=tk.Label(self, text=  "Release:")
        self.label.grid(row = 0, column = 0, sticky=sticky)
        
        self.hyperlink=ReleaseLink(self)
        self.hyperlink.grid(row = 0, column = 1,sticky="NSEW")
        
        self.release=release
        self.news_count=0
        self.news_pos=0
        self.minutes=0
        self.latest={}
        self.update()
        #self.hyperlink.bind('<Configure>', self.hyperlink.configure_event)
        
        
    def update(self):    
        self.release_thread()
        self.after(1000, self.release_update)
        
    def version2number(self,version):
        major,minor,patch=version.split('.')
        return (int(major)*1000000)+(int(minor)*1000)+int(patch)

    def release_thread(self):    
        ReleaseThread(self).start()
        
    def release_pull(self):
        self.latest={}
        r = requests.get("https://api.github.com/repos/VAKazakov/EDMC-Triumvirate/releases/latest")
        latest=r.json()
        #debug(latest)
        if not r.status_code == requests.codes.ok:
            
            error("Error fetching release from github")
            error(r.status_code)
            error(r.json())
            
        else:
            self.latest=latest
            debug("latest release downloaded")
       
        
        
    def release_update(self):

        
        
            
        if self.latest:
            debug("Latest is not null")
            
            
            #checjed again in an hour
            self.after(RELEASE_CYCLE, self.update)    
            
            #self.latest=requests.get("https://api.github.com/repos/VAKazakov/EDMC-Triumvirate/releases/latest").json()
            
            current=self.version2number(self.release)
            release=self.version2number(self.latest.get("tag_name"))
            
            self.hyperlink['url'] = self.latest.get("html_url")
            self.hyperlink['text'] = "EDMC-Triumvirate: {}".format(self.latest.get("tag_name"))

            if current==release:
                self.grid_remove()
            elif current > release:
                self.hyperlink['text'] = "Experimental Release {}".format(self.release)
                self.grid()
            else:
                
                if self.auto.get() == 1:
                    self.hyperlink['text'] = "Release {}  Installed Please Restart".format(self.latest.get("tag_name"))     
                    self.installer(self.latest.get("tag_name"))
                else:
                    self.hyperlink['text'] = "Please Upgrade {}".format(self.latest.get("tag_name"))
                    if self.novoices.get() != 1:
                        Player(Release.plugin_dir,["sounds\\prefix.wav","sounds\\nag1.wav"]).start()
                self.grid()
        else:
            debug("Latest is null")
            self.after(1000,self.release_update)
    
    def plugin_prefs(self, parent, cmdr, is_beta,gridrow):
        "Called to get a tk Frame for the settings dialog."

        self.auto=tk.IntVar(value=config.getint("AutoUpdate"))
        self.rmbackup=tk.IntVar(value=config.getint("RemoveBackup"))
        self.novoices=tk.IntVar(value=config.getint("NoVoices"))
        
        frame = nb.Frame(parent)
        frame.columnconfigure(2, weight=1)
        frame.grid(row = gridrow, column = 0,sticky="NSEW")
        nb.Checkbutton(frame, text="Auto Update This Plugin", variable=self.auto).grid(row = 0, column = 0,sticky="NW")
        nb.Checkbutton(frame, text="Remove backup", variable=self.rmbackup).grid(row = 0, column = 1,sticky="NW")
        nb.Checkbutton(frame, text="Stop talking to me", variable=self.novoices).grid(row = 0, column = 2,sticky="NW")
        
        return frame

    def prefs_changed(self, cmdr, is_beta):
        "Called when the user clicks OK on the settings dialog."
        config.set('AutoUpdate', self.auto.get())      
        config.set('RemoveBackup', self.rmbackup.get())      
        config.set('NoVoices', self.novoices.get())      
        
    def installer(self,tag_name):
        # need to add some defensive code around this
        download=requests.get("https://github.com/VAKazakov/EDMC-Triumvirate/archive/{}.zip".format(tag_name), stream=True)
        z = zipfile.ZipFile(StringIO.StringIO(download.content))
        z.extractall(os.path.dirname(Release.plugin_dir))
        
        #disable first in case we can't delete it
        os.rename(Release.plugin_dir,"{}.disabled".format(Release.plugin_dir))
        
        #keep a backup of the old release
        if self.rmbackup.get() == 1:
            shutil.rmtree("{}.disabled".format(Release.plugin_dir))
        
        Release.plugin_dir=os.path.join(os.path.dirname(Release.plugin_dir),"EDMC-Triumvirate-{}".format(tag_name))
        
    @classmethod            
    def get_auto(cls):
        return tk.IntVar(value=config.getint("AutoUpdate")).get()
        
    @classmethod    
    def plugin_start(cls,plugin_dir):
        cls.plugin_dir=plugin_dir

def recursive_overwrite(src, dest, ignore=None):
    if os.path.isdir(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        files = os.listdir(src)
        if ignore is not None:
            ignored = ignore(src, files)
        else:
            ignored = set()
        for f in files:
            if f not in ignored:
                recursive_overwrite(os.path.join(src, f), 
                                    os.path.join(dest, f), 
                                    ignore)
    else:
        shutil.copyfile(src, dest)