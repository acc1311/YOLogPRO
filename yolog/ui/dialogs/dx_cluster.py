# -*- coding: utf-8 -*-
"""ui/dialogs/dx_cluster.py — DX Cluster client telnet GUI"""
import re, datetime, threading, socket, time, tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from collections import deque
from ..theme import TH
from ...core.dxcc import DXCC
from ...core.bands import freq2band, BANDS_ALL

class DXClusterWindow(tk.Toplevel):
    DEFAULT_CLUSTERS = [
        "dxc.yo8acr.ro:7300","cluster.dl9gtb.de:7300","dx.db0sue.de:7300",
        "www.dxsummit.fi:7300","gb7mbc.spoo.org:7300",
    ]

    def __init__(self, parent, on_spot=None):
        super().__init__(parent)
        self.on_spot=on_spot; self.title(" DX Cluster — YO Log PRO v19")
        try: sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        except: sw,sh=1366,768
        self.geometry(f"{min(900,int(sw*.9))}x{min(560,int(sh*.85))}")
        self.configure(bg=TH["bg"])
        self._sock=None; self._thread=None; self._stop_evt=threading.Event()
        self._spots=[]; self._queue=deque(maxlen=200); self._connected=False
        self._build(); self._tick()

    def _build(self):
        tb=tk.Frame(self,bg=TH["header_bg"],pady=4); tb.pack(fill="x")
        tk.Label(tb,text="Cluster:",bg=TH["header_bg"],fg=TH["fg"],font=("Consolas",10)).pack(side="left",padx=4)
        self._cluster_v=tk.StringVar(value=self.DEFAULT_CLUSTERS[0])
        ttk.Combobox(tb,textvariable=self._cluster_v,values=self.DEFAULT_CLUSTERS,width=28,font=("Consolas",10)).pack(side="left",padx=4)
        tk.Label(tb,text="Call:",bg=TH["header_bg"],fg=TH["fg"],font=("Consolas",10)).pack(side="left")
        self._call_e=tk.Entry(tb,width=10,bg=TH["entry_bg"],fg=TH["gold"],font=("Consolas",10),insertbackground=TH["fg"]); self._call_e.pack(side="left",padx=4)
        self._conn_btn=tk.Button(tb,text="> Conectare",command=self._connect,bg=TH["ok"],fg="white",font=("Consolas",10)); self._conn_btn.pack(side="left",padx=4)
        tk.Button(tb,text="[] Stop",command=self._disconnect,bg=TH["err"],fg="white",font=("Consolas",10)).pack(side="left",padx=2)
        self._status_lbl=tk.Label(tb,text="o Deconectat",bg=TH["header_bg"],fg=TH["err"],font=("Consolas",9)); self._status_lbl.pack(side="right",padx=8)

        ff=tk.Frame(self,bg=TH["bg"],pady=2); ff.pack(fill="x",padx=6)
        tk.Label(ff,text="Filtru bandă:",bg=TH["bg"],fg=TH["fg"],font=("Consolas",9)).pack(side="left")
        self._fband_v=tk.StringVar(value="Toate")
        fcb=ttk.Combobox(ff,textvariable=self._fband_v,values=["Toate"]+BANDS_ALL,state="readonly",width=8); fcb.pack(side="left",padx=4); fcb.bind("<<ComboboxSelected>>",lambda e:self._refresh_spots())
        tk.Label(ff,text="Filtru call:",bg=TH["bg"],fg=TH["fg"],font=("Consolas",9)).pack(side="left",padx=(8,0))
        self._fcall_v=tk.StringVar()
        fe=tk.Entry(ff,textvariable=self._fcall_v,width=10,bg=TH["entry_bg"],fg=TH["fg"],font=("Consolas",9),insertbackground=TH["fg"]); fe.pack(side="left",padx=4); fe.bind("<KeyRelease>",lambda e:self._refresh_spots())
        self._spot_count_lbl=tk.Label(ff,text="0",bg=TH["bg"],fg=TH["gold"],font=("Consolas",9,"bold")); self._spot_count_lbl.pack(side="right")

        tf=tk.Frame(self,bg=TH["bg"]); tf.pack(fill="both",expand=True,padx=6,pady=3)
        cols=("time","dx","freq","band","mode","country","comment","spotter")
        self._tree=ttk.Treeview(tf,columns=cols,show="headings",selectmode="browse")
        for col,hdr,w in [("time","UTC",55),("dx","DX Call",95),("freq","Freq kHz",80),("band","Bandă",55),("mode","Mod",50),("country","Țara",90),("comment","Comment",160),("spotter","Spotter",90)]:
            self._tree.heading(col,text=hdr); self._tree.column(col,width=w,anchor="center")
        vsb=ttk.Scrollbar(tf,orient="vertical",command=self._tree.yview); self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left",fill="both",expand=True); vsb.pack(side="right",fill="y")
        self._tree.bind("<Double-1>",self._on_spot_dbl); self._tree.bind("<Return>",self._on_spot_dbl)
        self._tree.bind("<MouseWheel>",lambda e:self._tree.yview_scroll(int(-1*(e.delta/120)),"units"))
        self._tree.bind("<Button-4>",lambda e:self._tree.yview_scroll(-1,"units")); self._tree.bind("<Button-5>",lambda e:self._tree.yview_scroll(1,"units"))

        rf=tk.Frame(self,bg=TH["bg"]); rf.pack(fill="x",padx=6)
        tk.Label(rf,text="Raw cluster:",bg=TH["bg"],fg=TH["fg"],font=("Consolas",8)).pack(anchor="w")
        self._raw_box=scrolledtext.ScrolledText(rf,height=5,bg=TH["entry_bg"],fg=TH["ok"],font=("Consolas",8),state="disabled",insertbackground=TH["fg"]); self._raw_box.pack(fill="x")
        cf2=tk.Frame(self,bg=TH["bg"]); cf2.pack(fill="x",padx=6,pady=3)
        self._cmd_e=tk.Entry(cf2,bg=TH["entry_bg"],fg=TH["gold"],font=("Consolas",10),insertbackground=TH["fg"]); self._cmd_e.pack(side="left",fill="x",expand=True); self._cmd_e.bind("<Return>",self._send_cmd)
        tk.Button(cf2,text="Trimite",command=self._send_cmd,bg=TH["accent"],fg="white",font=("Consolas",10)).pack(side="left",padx=4)

    def _connect(self):
        addr=self._cluster_v.get().strip(); call=self._call_e.get().strip().upper()
        if not addr: messagebox.showerror("DX Cluster","Selectați un cluster!"); return
        if not call: messagebox.showerror("DX Cluster","Introduceți indicativul!"); return
        host,_,port_s=addr.partition(":")
        try: port=int(port_s) if port_s else 7300
        except: port=7300
        self._disconnect(); self._stop_evt.clear()
        self._thread=threading.Thread(target=self._run,args=(host,port,call),daemon=True); self._thread.start()

    def _disconnect(self):
        self._stop_evt.set(); self._connected=False
        try:
            if self._sock: self._sock.close()
        except OSError:
            pass
        self._sock=None

    def _run(self,host,port,call):
        try:
            self._sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM); self._sock.settimeout(10); self._sock.connect((host,port))
            self._connected=True; self._queue.append(("status","o Conectat la "+host))
            buf=b""; t0=time.time()
            while time.time()-t0<8:
                chunk=self._sock.recv(256)
                if not chunk: break
                buf+=chunk
                if b"call" in buf.lower() or b"login" in buf.lower() or b">" in buf: break
            self._sock.sendall((call+"\r\n").encode("ascii",errors="ignore")); time.sleep(0.5)
            self._sock.settimeout(5); line_buf=""
            while not self._stop_evt.is_set():
                try:
                    data=self._sock.recv(512)
                    if not data: break
                    line_buf+=data.decode("ascii",errors="ignore")
                    while "\n" in line_buf:
                        line,line_buf=line_buf.split("\n",1); line=line.strip()
                        if line:
                            self._queue.append(("raw",line)); spot=self._parse_spot(line)
                            if spot: self._queue.append(("spot",spot))
                except socket.timeout: continue
                except (OSError, ConnectionResetError): break
        except Exception as e: self._queue.append(("status","o Eroare: "+str(e)))
        self._connected=False; self._queue.append(("status","o Deconectat"))
        # Auto-reconectare dacă deconectarea NU a fost intentionată (buton Stop)
        if not self._stop_evt.is_set():
            self._queue.append(("reconnect", None))

    def _parse_spot(self,line):
        spotter=""; freq_s=""; dx_call=""; comment=""
        m=re.match(r'DX\s+de\s+(\S+?)\s*:\s*(\d[\d.]+)\s+(\S+)\s*(.*)',line,re.IGNORECASE)
        if m: spotter=m.group(1); freq_s=m.group(2); dx_call=m.group(3); comment=m.group(4).strip()
        else:
            m2=re.match(r'DX\s+(\d[\d.]+)\s+(\w+)\s*(.*)',line,re.IGNORECASE)
            if m2: freq_s=m2.group(1); dx_call=m2.group(2); comment=m2.group(3).strip()
            else: return None
        try: freq_khz=float(re.sub(r'[^0-9.]','',freq_s))
        except: return None
        band=freq2band(freq_khz) or "?"; country,_=DXCC.lookup(dx_call)
        mode="SSB"
        for mo in ["CW","FT8","FT4","RTTY","PSK31","SSB","AM","FM","DIGI"]:
            if mo in comment.upper(): mode=mo; break
        return {"time":datetime.datetime.utcnow().strftime("%H:%M"),"dx":dx_call.upper(),"freq":str(freq_khz),"band":band,"mode":mode,"country":country,"comment":comment.strip()[:40],"spotter":spotter.upper()}

    def _tick(self):
        try:
            if not self.winfo_exists(): return
        except tk.TclError: return
        processed=0
        while self._queue and processed<20:
            item=self._queue.popleft(); kind=item[0]; data=item[1]
            if kind=="status":
                try: self._status_lbl.config(text=data,fg=TH["ok"] if "Conectat" in data and "De" not in data else TH["err"])
                except: pass
            elif kind=="raw":
                try:
                    self._raw_box.config(state="normal"); self._raw_box.insert("end",data+"\n"); self._raw_box.see("end"); self._raw_box.config(state="disabled")
                except: pass
            elif kind=="spot":
                self._spots.insert(0,data)
                if len(self._spots)>500: self._spots=self._spots[:500]
                self._refresh_spots()
            elif kind=="reconnect":
                # Reconectare automata dupa 15 secunde
                self.after(15000, self._auto_reconnect)
            processed+=1
        self.after(500,self._tick)

    def _refresh_spots(self):
        fb=self._fband_v.get(); fc=self._fcall_v.get().upper().strip()
        for row in self._tree.get_children(): self._tree.delete(row)
        shown=0
        for spot in self._spots:
            if fb!="Toate" and spot["band"]!=fb: continue
            if fc and fc not in spot["dx"] and fc not in spot["spotter"]: continue
            self._tree.insert("","end",values=(spot["time"],spot["dx"],spot["freq"],spot["band"],spot["mode"],spot["country"],spot["comment"],spot["spotter"]))
            shown+=1
            if shown>=200: break
        self._spot_count_lbl.config(text=str(shown))

    def _on_spot_dbl(self,event=None):
        sel=self._tree.selection()
        if not sel: return
        vals=self._tree.item(sel[0],"values")
        if vals and self.on_spot: self.on_spot(vals[1],vals[2])

    def _auto_reconnect(self):
        """Reconectare automată după pierderea conexiunii."""
        if self._connected or self._stop_evt.is_set():
            return  # Deja conectat sau stop manual
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        self._queue.append(("status", "o Reconectare automată..."))
        self._connect()

    def _send_cmd(self,event=None):
        cmd=self._cmd_e.get().strip()
        if not cmd or not self._sock: return
        try: self._sock.sendall((cmd+"\r\n").encode("ascii",errors="ignore")); self._cmd_e.delete(0,"end")
        except Exception as e: messagebox.showerror("DX Cluster",str(e))
