#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
import tkinter as tk
from tkinter import filedialog
import random

ROOT_DIR = os.path.expanduser("~/Bible")
DB_FILE = os.path.join(ROOT_DIR, "bible.db")

TRANSLATIONS = ["kjv","web","asv"]

TOPIC_WORDS = {
"faith":["faith","believe","trust"],
"love":["love","charity","kindness"],
"salvation":["save","salvation","redeem"],
"sin":["sin","sins","iniquity"],
"grace":["grace","mercy"]
}

TIMELINE=[
("Creation","genesis",1,1),
("Flood","genesis",6,1),
("Abraham Called","genesis",12,1),
("Exodus","exodus",12,31),
("Ten Commandments","exodus",20,1),
("Birth of Jesus","luke",2,1),
("Crucifixion","john",19,16),
("Resurrection","john",20,1),
("Pentecost","acts",2,1)
]

ATLAS_IMAGES={
"Exodus Route":"atlas/exodus.png",
"Paul Missionary Journey":"atlas/paul.png"
}

class BibleDB:

    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.create()

    def create(self):
        c=self.conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS verses(
        translation TEXT,
        book TEXT,
        chapter INT,
        verse INT,
        text TEXT,
        strongs TEXT
        )
        """)
        self.conn.commit()

    def add(self,translation,book,chapter,verse,text,strongs=""):
        c=self.conn.cursor()
        c.execute("INSERT INTO verses VALUES (?,?,?,?,?,?)",
        (translation,book,chapter,verse,text,strongs))
        self.conn.commit()

    def get(self,translation,book,chapter,verse):
        c=self.conn.cursor()
        r=c.execute(
        "SELECT text,strongs FROM verses WHERE translation=? AND book=? AND chapter=? AND verse=?",
        (translation,book,chapter,verse)).fetchone()
        return r if r else ("","")

    def search(self,word):
        c=self.conn.cursor()
        return c.execute(
        "SELECT translation,book,chapter,verse,text FROM verses WHERE text LIKE ? LIMIT 50",
        ("%"+word+"%",)).fetchall()


class TopicCluster:

    def detect(self,text):

        found=[]
        t=text.lower()

        for topic,words in TOPIC_WORDS.items():
            for w in words:
                if w in t:
                    found.append(topic)
                    break

        return found


class InterlinearWindow:

    def __init__(self,root,text,strongs):

        win=tk.Toplevel(root)
        win.title("Interlinear")

        frame=tk.Frame(win)
        frame.pack(fill="both",expand=True)

        words=text.split()

        for i,w in enumerate(words):
            tk.Label(frame,text=w).grid(row=0,column=i)

        if strongs:
            s=strongs.split()
            for i,w in enumerate(s):
                tk.Label(frame,text=w,fg="blue").grid(row=1,column=i)


class ParallelViewer:

    def __init__(self,root,db,book,chapter,verse):

        win=tk.Toplevel(root)
        win.title("Parallel Translations")

        for i,tr in enumerate(TRANSLATIONS):

            text,_=db.get(tr,book,chapter,verse)

            frame=tk.Frame(win)
            frame.pack(fill="x")

            tk.Label(frame,text=tr.upper(),font=("Arial",10,"bold")).pack(anchor="w")

            tk.Label(frame,text=text,wraplength=600,justify="left").pack(anchor="w")


class AtlasWindow:

    def __init__(self,root):

        win=tk.Toplevel(root)
        win.title("Bible Atlas")

        listbox=tk.Listbox(win)
        listbox.pack(side="left",fill="y")

        canvas=tk.Canvas(win,width=600,height=500,bg="white")
        canvas.pack(side="right",fill="both",expand=True)

        for k in ATLAS_IMAGES:
            listbox.insert("end",k)

        def show(evt):

            sel=listbox.curselection()
            if not sel:
                return

            key=list(ATLAS_IMAGES.keys())[sel[0]]
            path=os.path.join(ROOT_DIR,ATLAS_IMAGES[key])

            canvas.delete("all")

            if os.path.exists(path):
                img=tk.PhotoImage(file=path)
                canvas.image=img
                canvas.create_image(0,0,image=img,anchor="nw")
            else:
                canvas.create_text(200,200,text="Map image not found")

        listbox.bind("<<ListboxSelect>>",show)


class TimelineWindow:

    def __init__(self,root,app):

        win=tk.Toplevel(root)
        win.title("Timeline Explorer")

        listbox=tk.Listbox(win,width=30)
        listbox.pack(side="left",fill="y")

        text=tk.Text(win,width=80)
        text.pack(side="right",fill="both",expand=True)

        for e,b,c,v in TIMELINE:
            listbox.insert("end",e)

        def show(evt):

            sel=listbox.curselection()
            if not sel:
                return

            event,book,ch,v=TIMELINE[sel[0]]

            t,_=app.db.get("kjv",book,ch,v)

            text.delete("1.0","end")
            text.insert("end",event+"\n\n"+t)

        listbox.bind("<<ListboxSelect>>",show)


class BibleApp:

    def __init__(self,root):

        self.root=root
        root.title("Advanced Bible Study")

        self.db=BibleDB()
        self.cluster=TopicCluster()

        self.book="john"
        self.chapter=3
        self.verse=16

        self.build()

    def build(self):

        menu=tk.Menu(self.root)
        self.root.config(menu=menu)

        tools=tk.Menu(menu,tearoff=0)
        menu.add_cascade(label="Tools",menu=tools)

        tools.add_command(label="Parallel Viewer",command=self.parallel)
        tools.add_command(label="Interlinear",command=self.interlinear)
        tools.add_command(label="Search",command=self.search)
        tools.add_command(label="Timeline Explorer",command=self.timeline)
        tools.add_command(label="Bible Atlas",command=self.atlas)

        frame=tk.Frame(self.root)
        frame.pack(fill="both",expand=True)

        self.text=tk.Text(frame,bg="black",fg="lime",wrap="word")
        self.text.pack(fill="both",expand=True)

        nav=tk.Frame(self.root)
        nav.pack()

        tk.Button(nav,text="Prev",command=self.prev).pack(side="left")
        tk.Button(nav,text="Next",command=self.next).pack(side="left")
        tk.Button(nav,text="Study",command=self.study).pack(side="left")

        self.display()

    def display(self):

        t,_=self.db.get("kjv",self.book,self.chapter,self.verse)

        self.text.delete("1.0","end")

        self.text.insert("end",f"{self.book} {self.chapter}:{self.verse}\n\n{t}\n\n")

        topics=self.cluster.detect(t)

        if topics:
            self.text.insert("end","Topics:\n")
            for tp in topics:
                self.text.insert("end",tp+"\n")

    def prev(self):

        self.verse-=1
        if self.verse<1:
            self.verse=1
        self.display()

    def next(self):

        self.verse+=1
        self.display()

    def study(self):

        t,s=self.db.get("kjv",self.book,self.chapter,self.verse)

        win=tk.Toplevel(self.root)
        win.title("Passage Study")

        text=tk.Text(win,width=90,height=35)
        text.pack(fill="both",expand=True)

        text.insert("end",t+"\n\n")

        topics=self.cluster.detect(t)

        text.insert("end","Detected Topics\n\n")

        for tp in topics:
            text.insert("end",tp+"\n")

    def search(self):

        win=tk.Toplevel(self.root)

        entry=tk.Entry(win,width=40)
        entry.pack()

        result=tk.Text(win,width=90,height=30)
        result.pack()

        def run():

            result.delete("1.0","end")

            for tr,b,c,v,t in self.db.search(entry.get()):
                result.insert("end",f"{tr} {b} {c}:{v}\n{t}\n\n")

        tk.Button(win,text="Search",command=run).pack()

    def parallel(self):

        ParallelViewer(self.root,self.db,self.book,self.chapter,self.verse)

    def interlinear(self):

        t,s=self.db.get("kjv",self.book,self.chapter,self.verse)
        InterlinearWindow(self.root,t,s)

    def timeline(self):

        TimelineWindow(self.root,self)

    def atlas(self):

        AtlasWindow(self.root)


def main():

    root=tk.Tk()
    app=BibleApp(root)
    root.mainloop()


if __name__=="__main__":
    main()
