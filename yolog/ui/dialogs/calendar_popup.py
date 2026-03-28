# -*- coding: utf-8 -*-
"""ui/dialogs/calendar_popup.py"""
import calendar, datetime, tkinter as tk
from ..theme import TH

class CalendarPopup(tk.Toplevel):
    def __init__(self, parent, current_date_str, callback):
        super().__init__(parent)
        self.callback=callback; self.overrideredirect(True); self.configure(bg=TH["bg"]); self.resizable(False,False)
        try: dt=datetime.datetime.strptime(current_date_str.strip(),"%Y-%m-%d")
        except: dt=datetime.datetime.utcnow()
        self.year=dt.year; self.month=dt.month; self.sel_day=dt.day
        self._build(); self._render()
        self.update_idletasks()
        px=parent.winfo_rootx(); py=parent.winfo_rooty()+parent.winfo_height()+2
        sw=self.winfo_screenwidth(); sh=self.winfo_screenheight()
        w=self.winfo_width(); h=self.winfo_height()
        if px+w>sw: px=sw-w-4
        if py+h>sh: py=parent.winfo_rooty()-h-2
        self.geometry(f"+{px}+{py}")
        self.grab_set(); self.focus_set()
        self.bind("<Escape>",lambda e:self.destroy())
        self.bind("<FocusOut>",lambda e:self.after(100,lambda:self.destroy() if not self.focus_displayof() else None))

    def _build(self):
        hf=tk.Frame(self,bg=TH["bg"]); hf.pack(fill="x",padx=4,pady=4)
        tk.Button(hf,text="<",command=self._prev,bg=TH["btn_bg"],fg=TH["btn_fg"],font=("Consolas",10),bd=0,cursor="hand2").pack(side="left")
        self.hdr_lbl=tk.Label(hf,text="",bg=TH["bg"],fg=TH.get("gold",TH["fg"]),font=("Consolas",11,"bold"),width=16); self.hdr_lbl.pack(side="left",expand=True)
        tk.Button(hf,text=">",command=self._next,bg=TH["btn_bg"],fg=TH["btn_fg"],font=("Consolas",10),bd=0,cursor="hand2").pack(side="right")
        wf=tk.Frame(self,bg=TH["bg"]); wf.pack(fill="x",padx=4)
        for i,d in enumerate(["Lu","Ma","Mi","Jo","Vi","Sâ","Du"]):
            fg=TH.get("err","#e74c3c") if i==6 else TH["fg"]
            tk.Label(wf,text=d,bg=TH["bg"],fg=fg,font=("Consolas",9,"bold"),width=3).grid(row=0,column=i,padx=1)
        self.grid_f=tk.Frame(self,bg=TH["bg"]); self.grid_f.pack(fill="both",padx=4,pady=(2,4))
        bf=tk.Frame(self,bg=TH["bg"]); bf.pack(pady=(0,4))
        tk.Button(bf,text="Azi",command=self._today,bg=TH["accent"],fg="white",font=("Consolas",9),cursor="hand2",bd=0,relief="flat").pack()

    def _render(self):
        for w in self.grid_f.winfo_children(): w.destroy()
        LUNI=["Ianuarie","Februarie","Martie","Aprilie","Mai","Iunie","Iulie","August","Septembrie","Octombrie","Noiembrie","Decembrie"]
        self.hdr_lbl.config(text=f"{LUNI[self.month-1]} {self.year}")
        cal=calendar.monthcalendar(self.year,self.month); today=datetime.datetime.utcnow()
        for r,week in enumerate(cal):
            for c,day in enumerate(week):
                if day==0: tk.Label(self.grid_f,text="",bg=TH["bg"],width=3).grid(row=r,column=c,padx=1,pady=1); continue
                is_sel=day==self.sel_day; is_today=day==today.day and self.month==today.month and self.year==today.year; is_sun=c==6
                if is_sel: bg=TH["accent"]; fg="white"
                elif is_today: bg=TH.get("gold","#f39c12"); fg=TH["bg"]
                elif is_sun: bg=TH["bg"]; fg=TH.get("err","#e74c3c")
                else: bg=TH["bg"]; fg=TH["fg"]
                btn=tk.Button(self.grid_f,text=str(day),bg=bg,fg=fg,font=("Consolas",9,"bold" if is_sel or is_today else "normal"),bd=0,relief="flat",cursor="hand2",command=lambda d=day:self._pick(d))
                btn.grid(row=r,column=c,padx=1,pady=1)
                btn.bind("<Enter>",lambda e,b=btn,d=day:b.config(bg=TH["accent"],fg="white") if d!=self.sel_day else None)
                btn.bind("<Leave>",lambda e,b=btn,bg_=bg,fg_=fg:b.config(bg=bg_,fg=fg_))

    def _pick(self,day):
        self.sel_day=day; self.callback(f"{self.year:04d}-{self.month:02d}-{day:02d}"); self.destroy()
    def _today(self):
        t=datetime.datetime.utcnow(); self.year=t.year; self.month=t.month; self._pick(t.day)
    def _prev(self):
        self.month-=1
        if self.month<1: self.month=12; self.year-=1
        self.sel_day=min(self.sel_day,calendar.monthrange(self.year,self.month)[1]); self._render()
    def _next(self):
        self.month+=1
        if self.month>12: self.month=1; self.year+=1
        self.sel_day=min(self.sel_day,calendar.monthrange(self.year,self.month)[1]); self._render()
