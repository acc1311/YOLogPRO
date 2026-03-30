# -*- coding: utf-8 -*-
"""ui/dialogs/theme_dlg.py — Dialog editare teme și culori personalizate"""
import tkinter as tk
from tkinter import ttk, colorchooser
from ..theme import TH, THEMES
from ... import i18n

def _rg(d,p,iw,ih):
    try: sw,sh=d.winfo_screenwidth(),d.winfo_screenheight()
    except: sw,sh=1366,768
    w,h=min(iw,int(sw*.92)),min(ih,int(sh*.88))
    try: x=p.winfo_rootx()+(p.winfo_width()-w)//2; y=p.winfo_rooty()+(p.winfo_height()-h)//2
    except: x,y=(sw-w)//2,(sh-h)//2
    d.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")

class ThemeDialog(tk.Toplevel):
    def __init__(self, parent, current_theme, custom_colors):
        super().__init__(parent)
        self.result=None; self.current_theme=current_theme; self.custom=dict(custom_colors)
        self.title(" Teme și Culori / Themes & Colors"); _rg(self,parent,640,560)
        self.configure(bg=TH["bg"]); self.transient(parent); self.grab_set()
        self._build()

    def _build(self):
        lo={"bg":TH["bg"],"fg":TH["fg"],"font":("Consolas",11)}
        tk.Label(self,text=" Teme / Themes",bg=TH["bg"],fg=TH["gold"],
                 font=("Consolas",13,"bold")).pack(pady=(12,4))

        # Seletor temă predefinită
        tf=tk.Frame(self,bg=TH["bg"]); tf.pack(fill="x",padx=20,pady=4)
        tk.Label(tf,text="Temă predefinită:",**lo).pack(side="left")
        self._theme_v=tk.StringVar(value=self.current_theme)
        tcb=ttk.Combobox(tf,textvariable=self._theme_v,values=list(THEMES.keys()),
                          state="readonly",width=22,font=("Consolas",11))
        tcb.pack(side="left",padx=8)
        tk.Button(tf,text="R Aplică",command=self._apply_preset,
                  bg=TH["accent"],fg="white",font=("Consolas",10)).pack(side="left",padx=4)

        # Preview
        self._prev_frame=tk.Frame(self,bg=TH["bg"],bd=1,relief="solid")
        self._prev_frame.pack(fill="x",padx=20,pady=6)
        self._draw_preview(self.custom if self.custom else THEMES.get(self.current_theme,TH))

        tk.Frame(self,bg=TH["warn"],height=1).pack(fill="x",padx=20,pady=4)
        tk.Label(self,text=" Personalizare culori:",bg=TH["bg"],fg=TH["cyan"],
                 font=("Consolas",11,"bold")).pack(anchor="w",padx=20)

        # Grid culori
        cf=tk.Frame(self,bg=TH["bg"]); cf.pack(fill="both",expand=True,padx=20,pady=4)
        self._color_entries={}
        color_labels={"bg":"Fundal","fg":"Text","accent":"Accent","entry_bg":"Câmpuri",
                      "header_bg":"Header","gold":"Clock/Score","ok":"OK","err":"Eroare","warn":"Avertisment"}
        base=self.custom if self.custom else THEMES.get(self.current_theme,TH)
        for i,(k,lbl) in enumerate(color_labels.items()):
            r,c=divmod(i,3)
            fr=tk.Frame(cf,bg=TH["bg"]); fr.grid(row=r,column=c,padx=6,pady=3,sticky="w")
            tk.Label(fr,text=lbl,bg=TH["bg"],fg=TH["fg"],font=("Consolas",9)).pack(anchor="w")
            ef=tk.Frame(fr,bg=TH["bg"]); ef.pack(fill="x")
            e=tk.Entry(ef,width=9,bg=TH["entry_bg"],fg=TH["fg"],font=("Consolas",10),
                       insertbackground=TH["fg"],justify="center")
            e.insert(0,base.get(k,"#ffffff")); e.pack(side="left")
            sw=tk.Label(ef,text="  ",bg=base.get(k,"#ffffff"),width=2); sw.pack(side="left",padx=2)
            def _pick(ev,key=k,entry=e,swatch=sw):
                col=colorchooser.askcolor(color=entry.get(),title=f"Culoare: {key}")
                if col and col[1]:
                    entry.delete(0,"end"); entry.insert(0,col[1])
                    try: swatch.config(bg=col[1])
                    except: pass
            e.bind("<Double-Button-1>",_pick); sw.bind("<Button-1>",_pick)
            e.bind("<FocusOut>",lambda ev,s=sw,en=e: self._upd_sw(ev,s,en))
            self._color_entries[k]=e

        bf=tk.Frame(self,bg=TH["bg"]); bf.pack(pady=10)
        tk.Button(bf,text=" Salvează",command=self._save,bg=TH["ok"],fg="white",
                  font=("Consolas",11,"bold")).pack(side="left",padx=6)
        tk.Button(bf,text="R Reset",command=self._reset,bg=TH["warn"],fg="white",
                  font=("Consolas",10)).pack(side="left",padx=6)
        tk.Button(bf,text=" Anulează",command=self.destroy,bg=TH["btn_bg"],fg="white",
                  font=("Consolas",11)).pack(side="left",padx=6)

    def _upd_sw(self,ev,sw,e):
        try: sw.config(bg=e.get())
        except: pass

    def _draw_preview(self,colors):
        for w in self._prev_frame.winfo_children(): w.destroy()
        pf=tk.Frame(self._prev_frame,bg=colors.get("bg","#000"),pady=4); pf.pack(fill="x")
        tk.Label(pf,text=" YO Log PRO v19 ",bg=colors.get("header_bg","#000"),
                 fg=colors.get("gold","#ffd700"),font=("Consolas",10,"bold")).pack(side="left",padx=6)
        rf=tk.Frame(self._prev_frame,bg=colors.get("bg","#000"),pady=2); rf.pack(fill="x",padx=6)
        tk.Entry(rf,width=10,bg=colors.get("entry_bg","#000"),
                 fg=colors.get("gold","#ffd700"),font=("Consolas",10)).pack(side="left",padx=4)
        tk.Button(rf,text="LOG",bg=colors.get("accent","#1f6feb"),fg="white",
                  font=("Consolas",9,"bold")).pack(side="left",padx=4)
        for lbl,ck in [(" OK ",  "ok"),(" WARN ","warn"),(" ERR ","err")]:
            tk.Label(rf,text=lbl,bg=colors.get("bg","#000"),
                     fg=colors.get(ck,"#fff"),font=("Consolas",9,"bold")).pack(side="left")

    def _apply_preset(self):
        preset=THEMES.get(self._theme_v.get(),{})
        for k,e in self._color_entries.items():
            e.delete(0,"end"); e.insert(0,preset.get(k,TH.get(k,"#ffffff")))
            for ch in e.master.winfo_children():
                if isinstance(ch,tk.Label):
                    try: ch.config(bg=preset.get(k,"#ffffff"))
                    except: pass
        self._draw_preview(preset)

    def _reset(self):
        self._theme_v.set("Dark Blue (implicit)"); self._apply_preset()

    def _save(self):
        colors=dict(THEMES.get(self._theme_v.get(),TH))
        for k,e in self._color_entries.items():
            v=e.get().strip()
            if v.startswith("#") and len(v) in (4,7): colors[k]=v
        self.result={"theme":self._theme_v.get(),"colors":colors}
        self.destroy()
