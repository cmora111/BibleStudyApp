#!/usr/bin/env python3
import os
import sqlite3
import tkinter as tk
from tkinter import filedialog

ROOT_DIR = os.path.expanduser("~/BibleStudy")
DB_FILE = os.path.join(ROOT_DIR,"bible.db")

TRANSLATIONS = ["kjv","web","asv","esv"]

TOPICS = {
"faith":["faith","believe","trust"],
"love":["love","charity","kindness"],
"salvation":["save","salvation","redeem"],
"sin":["sin","iniquity","transgression"],
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

class BibleDB:

    def __init__(self):
        os.makedirs(ROOT_DIR,exist_ok=True)
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

    def insert(self,tr,book,ch,v,text,strongs=""):
        c=self.conn.cursor()
        c.execute("INSERT INTO verses VALUES (?,?,?,?,?,?)",
        (tr,book,ch,v,text,strongs))
        self.conn.commit()

    def get(self,tr,book,ch,v):
        c=self.conn.cursor()
        r=c.execute(
        "SELECT text,strongs FROM verses WHERE translation=? AND book=? AND chapter=? AND verse=?",
        (tr,book,ch,v)).fetchone()
        if r:
            return r
        return ("","")

    def search(self,word):
        c=self.conn.cursor()
        return c.execute(
        "SELECT translation,book,chapter,verse,text FROM verses WHERE text LIKE ? LIMIT 100",
        ("%"+word+"%",)).fetchall()


class TopicEngine:

    def detect(self,text):
        t=text.lower()
        found=[]
        for topic,words in TOPICS.items():
            for w in words:
                if w in t:
                    found.append(topic)
                    break
        return found


class ParallelWindow:

    def __init__(self,root,db,book,ch,v):

        win=tk.Toplevel(root)
        win.title("Parallel Bible")

        for tr in TRANSLATIONS:

            text,_=db.get(tr,book,ch,v)

            frame=tk.Frame(win)
            frame.pack(fill="x")

            tk.Label(frame,text=tr.upper(),font=("Arial",10,"bold")).pack(anchor="w")
            tk.Label(frame,text=text,wraplength=700,justify="left").pack(anchor="w")


class InterlinearWindow:

    def __init__(self,root,text,strongs):

        win=tk.Toplevel(root)
        win.title("Interlinear")

        frame=tk.Frame(win)
        frame.pack()

        words=text.split()
        strong=strongs.split() if strongs else []

        for i,w in enumerate(words):
            tk.Label(frame,text=w).grid(row=0,column=i,padx=2)

        for i,s in enumerate(strong):
            tk.Label(frame,text=s,fg="blue").grid(row=1,column=i,padx=2)


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


class DiscoveryEngine:

    def discover(self,db,query):

        words=query.lower().split()
        results=[]

        for w in words:
            for tr,b,c,v,t in db.search(w):
                score=sum(word in t.lower() for word in words)
                results.append((score,tr,b,c,v,t))

        results.sort(reverse=True)
        return results[:30]


class BibleApp:

    def __init__(self,root):

        self.root=root
        root.title("Advanced Bible Study")

        self.db=BibleDB()
        self.topic=TopicEngine()
        self.discovery=DiscoveryEngine()

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
        tools.add_command(label="Smart Discovery",command=self.discover)
        tools.add_command(label="Timeline Explorer",command=self.timeline)
        tools.add_command(label="Import Bible File",command=self.import_bible)

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

        topics=self.topic.detect(t)

        if topics:
            self.text.insert("end","Topics:\n")
            for tp in topics:
                self.text.insert("end",tp+"\n")

    def prev(self):

        self.verse=max(1,self.verse-1)
        self.display()

    def next(self):

        self.verse+=1
        self.display()

    def study(self):

        t,_=self.db.get("kjv",self.book,self.chapter,self.verse)

        win=tk.Toplevel(self.root)
        win.title("Study Mode")

        text=tk.Text(win,width=90,height=35)
        text.pack(fill="both",expand=True)

        text.insert("end",t+"\n\n")

        topics=self.topic.detect(t)

        text.insert("end","Topics\n\n")

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

    def discover(self):

        win=tk.Toplevel(self.root)

        entry=tk.Entry(win,width=40)
        entry.pack()

        result=tk.Text(win,width=90,height=30)
        result.pack()

        def run():

            result.delete("1.0","end")

            for score,tr,b,c,v,t in self.discovery.discover(self.db,entry.get()):
                result.insert("end",f"{tr} {b} {c}:{v}\n{t}\n\n")

        tk.Button(win,text="Discover",command=run).pack()

    def parallel(self):

        ParallelWindow(self.root,self.db,self.book,self.chapter,self.verse)

    def interlinear(self):

        t,s=self.db.get("kjv",self.book,self.chapter,self.verse)
        InterlinearWindow(self.root,t,s)

    def timeline(self):

        TimelineWindow(self.root,self)

    def import_bible(self):

        file=filedialog.askopenfilename(title="Select Bible File")

        if not file:
            return

        tr=os.path.basename(file).split(".")[0].lower()

        with open(file) as f:

            for line in f:

                parts=line.strip().split("|")

                if len(parts)<4:
                    continue

                book,chapter,verse,text=parts[:4]

                self.db.insert(tr,book,int(chapter),int(verse),text)

        print("Bible imported:",tr)


def main():

    root=tk.Tk()
    app=BibleApp(root)
    root.mainloop()


if __name__=="__main__":
    main()
