#!/usr/bin/env python3

import os
import sys
import json
import tkinter as tk

ROOT_DIR="/home/mora/Bible"

INDEX_FILE=os.path.join(ROOT_DIR,".verse_index.json")
WORKSPACE_FILE=os.path.join(ROOT_DIR,".workspace.json")


#################################################
# BOOK STRUCTURE
#################################################

OLD_TESTAMENT=[
"genesis-50.txt","exodus-40.txt","levit.txt","numbers.txt","deut.txt",
"joshua.txt","judges.txt","ruth.txt",
"1samuel.txt","2samuel.txt",
"1kings.txt","2kings.txt",
"1chron.txt","2chron.txt",
"ezra.txt","nehemiah.txt","esther.txt",
"job.txt","psalms.txt","proverbs.txt",
"eccl.txt","song.txt",
"isaiah.txt","jeremiah.txt","lament.txt",
"ezekiel.txt","daniel.txt",
"hosea.txt","joel.txt","amos.txt",
"obadiah.txt","jonah.txt","micah.txt",
"nahum.txt","habakkuk.txt","zeph.txt",
"haggai.txt","zech.txt","malachi.txt"
]

NEW_TESTAMENT=[
"matthew.txt","mark.txt","luke.txt","john.txt","acts.txt",
"romans.txt",
"1corinth.txt","2corinth.txt",
"galatian.txt","ephesian.txt","philipp.txt","colossia.txt",
"1thess.txt","2thess.txt",
"1timothy.txt","2timothy.txt","titus.txt","philemon.txt",
"hebrews.txt","james.txt",
"1peter.txt","2peter.txt",
"1john.txt","2john.txt","3john.txt",
"jude.txt","rev.txt"
]


#################################################
# BIBLE LOADING
#################################################

def load_verse(file,ch,v):

    path=os.path.join(ROOT_DIR,file)

    if not os.path.exists(path):
        return ""

    with open(path) as f:

        for line in f:

            line=line.strip()

            if not line:
                continue

            parts=line.split("::")

            if len(parts)<3:
                continue

            if parts[0]==str(ch) and parts[1]==str(v):

                return parts[2]

    return ""


def load_chapter(file,ch):

    verses=[]

    path=os.path.join(ROOT_DIR,file)

    with open(path) as f:

        for line in f:

            parts=line.strip().split("::")

            if len(parts)<3:
                continue

            if parts[0]==str(ch):

                verses.append((parts[1],parts[2]))

    return verses


def load_book(file):

    verses=[]

    path=os.path.join(ROOT_DIR,file)

    with open(path) as f:

        for line in f:

            parts=line.strip().split("::")

            if len(parts)<3:
                continue

            verses.append((parts[0],parts[1],parts[2]))

    return verses


#################################################
# FAST SEARCH INDEX
#################################################

def build_index():

    index={}

    for file in os.listdir(ROOT_DIR):

        if not file.endswith(".txt"):
            continue

        path=os.path.join(ROOT_DIR,file)

        with open(path) as f:

            for line in f:

                parts=line.strip().split("::")

                if len(parts)<3:
                    continue

                ch,v,text=parts

                ref=f"{file}:{ch}:{v}"

                for w in text.lower().split():

                    index.setdefault(w,[]).append((ref,text))

    with open(INDEX_FILE,"w") as f:
        json.dump(index,f)


def load_index():

    if not os.path.exists(INDEX_FILE):
        build_index()

    with open(INDEX_FILE) as f:
        return json.load(f)


#################################################
# AI SEMANTIC SEARCH
#################################################

def semantic_score(q,verse):

    q=set(q.lower().split())
    v=set(verse.lower().split())

    return len(q & v)


def semantic_search(index,query):

    results=[]

    for word in query.lower().split():

        if word in index:

            for ref,text in index[word]:

                score=semantic_score(query,text)

                results.append((score,ref,text))

    results.sort(reverse=True)

    return results[:25]


#################################################
# WORKSPACE
#################################################

class Workspace:

    def __init__(self):

        self.notes={}
        self.bookmarks=[]

        self.load()

    def load(self):

        if not os.path.exists(WORKSPACE_FILE):
            return

        with open(WORKSPACE_FILE) as f:

            data=json.load(f)

        self.notes=data.get("notes",{})
        self.bookmarks=data.get("bookmarks",[])

    def save(self):

        data={
            "notes":self.notes,
            "bookmarks":self.bookmarks
        }

        with open(WORKSPACE_FILE,"w") as f:
            json.dump(data,f,indent=2)


#################################################
# GUI
#################################################

class BibleApp:

    def __init__(self,root):

        self.root=root
        root.title("Bible Study App")

        self.index=load_index()
        self.workspace=Workspace()

        self.build_ui()


#################################################
# UI
#################################################

    def build_ui(self):

        menu=tk.Menu(self.root)
        self.root.config(menu=menu)

        file=tk.Menu(menu,tearoff=0)
        menu.add_cascade(label="File",menu=file)

        file.add_command(label="Quit",command=self.root.quit)

        tools=tk.Menu(menu,tearoff=0)
        menu.add_cascade(label="Tools",menu=tools)

        tools.add_command(label="Search",command=self.search_window)
        tools.add_command(label="Topic Explorer",command=self.topic_window)

        frame=tk.Frame(self.root)
        frame.pack(fill="both",expand=True)

        book_frame=tk.Frame(frame)
        book_frame.pack(side="left",fill="y")

        self.make_book_grid(book_frame,"Old Testament",OLD_TESTAMENT)
        self.make_book_grid(book_frame,"New Testament",NEW_TESTAMENT)

        self.text=tk.Text(frame,bg="black",fg="lime",wrap="word")
        self.text.pack(fill="both",expand=True)



#################################################
# BOOK GRID
#################################################

    def make_book_grid(self,parent,title,books):

        lab=tk.Label(parent,text=title,font=("Arial",10,"bold"))
        lab.pack()

        grid=tk.Frame(parent)
        grid.pack()

        cols=3

        for i,b in enumerate(books):

            r=i//cols
            c=i%cols

            name=b.replace(".txt","")

            btn=tk.Button(
                grid,
                text=name,
                width=14,
                command=lambda f=b:self.select_chapter(f)
            )

            btn.grid(row=r,column=c,padx=2,pady=2)


#################################################
# CHAPTER SELECT
#################################################

    def select_chapter(self,file):

        win=tk.Toplevel(self.root)
        win.title("Select Chapter")

        for i in range(1,151):

            btn=tk.Button(
                win,
                text=i,
                width=4,
                command=lambda c=i:self.select_verse(file,c,win)
            )

            btn.grid(row=i//10,column=i%10)


#################################################
# VERSE SELECT
#################################################

    def select_verse(self,file,ch,chapter_win):

        chapter_win.destroy()

        win=tk.Toplevel(self.root)
        win.title("Select Verse")

        for i in range(1,80):

            btn=tk.Button(
                win,
                text=i,
                width=4,
                command=lambda v=i:self.display_verse(file,ch,v,win)
            )

            btn.grid(row=i//10,column=i%10)


#################################################
# DISPLAY FUNCTIONS
#################################################

    def display_verse(self,file,ch,v,win):

        win.destroy()

        verse=load_verse(file,ch,v)

        self.text.delete("1.0","end")

        ref=f"{file.replace('.txt','')} {ch}:{v}"

        self.text.insert("end",f"{ref}\n\n{verse}")


    def display_chapter(self,file,ch):

        self.text.delete("1.0","end")

        verses=load_chapter(file,ch)

        for v,text in verses:

            self.text.insert("end",f"{ch}:{v} {text}\n")


    def display_book(self,file):

        self.text.delete("1.0","end")

        verses=load_book(file)

        for ch,v,text in verses:

            self.text.insert("end",f"{ch}:{v} {text}\n")



#################################################
# SEARCH WINDOW
#################################################

    def search_window(self):

        win=tk.Toplevel(self.root)

        entry=tk.Entry(win,width=40)
        entry.pack()

        result=tk.Text(win,height=20,width=80)
        result.pack()

        def run():

            result.delete("1.0","end")

            query=entry.get()

            matches=semantic_search(self.index,query)

            for score,ref,text in matches:

                result.insert("end",f"{ref}\n{text}\n\n")

        tk.Button(win,text="Search",command=run).pack()


#################################################
# TOPIC EXPLORER
#################################################

    def topic_window(self):

        TOPICS={
        "Faith":[("hebrews.txt",11,1),("romans.txt",10,17)],
        "Love":[("1corinth.txt",13,4),("john.txt",13,34)],
        "Salvation":[("john.txt",3,16),("acts.txt",4,12)]
        }

        win=tk.Toplevel(self.root)

        for topic in TOPICS:

            btn=tk.Button(
                win,
                text=topic,
                command=lambda t=topic:self.show_topic(t,TOPICS)
            )

            btn.pack(fill="x")


    def show_topic(self,topic,TOPICS):

        self.text.delete("1.0","end")

        self.text.insert("end",f"Topic: {topic}\n\n")

        for file,ch,v in TOPICS[topic]:

            verse=load_verse(file,ch,v)

            ref=f"{file.replace('.txt','')} {ch}:{v}"

            self.text.insert("end",f"{ref}\n{verse}\n\n")


#################################################
# CLI MODE
#################################################

def cli():

    if len(sys.argv)<4:
        print("Usage: bible file chapter verse")
        return

    file=sys.argv[1]
    ch=sys.argv[2]
    v=sys.argv[3]

    print(load_verse(file,ch,v))


#################################################
# MAIN
#################################################

def main():

    if "-g" not in sys.argv and len(sys.argv)==4:
        cli()
        return

    root=tk.Tk()
    BibleApp(root)
    root.mainloop()


if __name__=="__main__":
    main()
