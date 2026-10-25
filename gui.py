"""
Smart Library Management System v2 — gui.py  (FINAL CLEAN VERSION)
"""
import tkinter as tk
from tkinter import ttk, messagebox
import time, os, sys

try:
    import cv2
    from PIL import Image, ImageTk
    CV2_OK = True
except ImportError:
    CV2_OK = False

from library_manager import LibraryManager
from qr_scanner      import QRScanner

BG='#0d1117'; BG_MID='#161b22'; BG_CARD='#21262d'
ACCENT='#e94560'; BLUE='#58a6ff'; GREEN='#3fb950'
ORANGE='#f78166'; RED='#ff4444'; FG='#f0f6fc'; FG_DIM='#8b949e'; BORDER='#30363d'


class SmartLibraryGUI:
    def __init__(self, root):
        self.root=root
        self.root.title("Smart Library Management System v2")
        self.root.geometry("1300x760")
        self.root.minsize(1050,640)
        self.root.configure(bg=BG)
        self.manager=LibraryManager()
        self.scanner=QRScanner()
        self.scanner.set_callback(self._on_qr_scanned)
        self.manager.on_event_callback=self._on_library_event
        self.manager.checker.on_status_callback=self._on_checker_status
        self.camera_active=False
        self._cam_after_id=None
        self.selected_book_id=None
        self._apply_styles()
        self._build_ui()
        self._start_camera()

    def _apply_styles(self):
        s=ttk.Style(); s.theme_use('clam')
        s.configure('TNotebook',background=BG,borderwidth=0)
        s.configure('TNotebook.Tab',background=BG_MID,foreground=FG_DIM,padding=[14,6],font=('Segoe UI',10))
        s.map('TNotebook.Tab',background=[('selected',BG_CARD)],foreground=[('selected',FG)])
        s.configure('Treeview',background=BG_MID,foreground=FG,fieldbackground=BG_MID,rowheight=30,font=('Segoe UI',9))
        s.configure('Treeview.Heading',background=BG_CARD,foreground=BLUE,font=('Segoe UI',9,'bold'))
        s.map('Treeview',background=[('selected',ACCENT)])

    def _btn(self,parent,text,command,bg=BG_CARD,fg=FG):
        return tk.Button(parent,text=text,command=command,bg=bg,fg=fg,
                         activebackground=bg,relief='flat',font=('Segoe UI',9),
                         padx=10,pady=4,cursor='hand2')

    def _set_status(self,msg):
        self._status_lbl.config(text=f"  {msg}")

    def _tick_clock(self):
        self._clock_lbl.config(text=time.strftime('%d %b %Y   %H:%M:%S'))
        self.root.after(1000,self._tick_clock)

    # ══ MAIN UI ══════════════════════════════════════════════════════════════
    def _build_ui(self):
        hdr=tk.Frame(self.root,bg='#0f1723',height=62)
        hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr,text="📚  Smart Library Management System v2",
                 font=('Segoe UI',17,'bold'),fg=ACCENT,bg='#0f1723').pack(side='left',padx=22,pady=10)
        rht=tk.Frame(hdr,bg='#0f1723'); rht.pack(side='right',padx=18)
        self._notify_dot=tk.Label(rht,text="●",fg=FG_DIM,bg='#0f1723',font=('Arial',13))
        self._notify_dot.pack(side='left')
        tk.Label(rht,text=" Notify  ",fg=FG_DIM,bg='#0f1723',font=('Segoe UI',9)).pack(side='left')
        self._conn_dot=tk.Label(rht,text="●",fg=RED,bg='#0f1723',font=('Arial',13))
        self._conn_dot.pack(side='left',padx=(10,0))
        self._conn_lbl=tk.Label(rht,text=" Pico W: Disconnected",fg=FG_DIM,bg='#0f1723',font=('Segoe UI',9))
        self._conn_lbl.pack(side='left')
        self._btn(rht,"⚡ Connect Pico",self._connect_pico_dialog,bg=ACCENT).pack(side='left',padx=12)

        nb=ttk.Notebook(self.root); nb.pack(fill='both',expand=True,padx=6,pady=4)
        self._tab_scanner=tk.Frame(nb,bg=BG); self._tab_books=tk.Frame(nb,bg=BG)
        self._tab_search=tk.Frame(nb,bg=BG);  self._tab_deadlines=tk.Frame(nb,bg=BG)
        self._tab_history=tk.Frame(nb,bg=BG); self._tab_settings=tk.Frame(nb,bg=BG)
        nb.add(self._tab_scanner,  text='📷  Scanner')
        nb.add(self._tab_books,    text='📖  Books')
        nb.add(self._tab_search,   text='🔍  Search')
        nb.add(self._tab_deadlines,text='⏰  Deadlines & Fines')
        nb.add(self._tab_history,  text='📋  History')
        nb.add(self._tab_settings, text='⚙️  Settings')
        self._build_scanner_tab(); self._build_books_tab()
        self._build_search_tab();  self._build_deadlines_tab()
        self._build_history_tab(); self._build_settings_tab()

        sb=tk.Frame(self.root,bg=BG_MID,height=26); sb.pack(fill='x',side='bottom'); sb.pack_propagate(False)
        self._status_lbl=tk.Label(sb,text="  System ready.",fg=FG_DIM,bg=BG_MID,font=('Segoe UI',9),anchor='w')
        self._status_lbl.pack(side='left',fill='x',expand=True)
        self._clock_lbl=tk.Label(sb,text="",fg=FG_DIM,bg=BG_MID,font=('Segoe UI',9))
        self._clock_lbl.pack(side='right',padx=12)
        self._tick_clock()

    # ══ SCANNER TAB ══════════════════════════════════════════════════════════
    def _build_scanner_tab(self):
        tab=self._tab_scanner
        left=tk.Frame(tab,bg=BG); left.pack(side='left',fill='both',expand=True,padx=(8,4),pady=8)
        cc=tk.Frame(left,bg=BORDER,padx=1,pady=1); cc.pack(fill='both',expand=True)
        ci=tk.Frame(cc,bg=BG_CARD); ci.pack(fill='both',expand=True)
        tk.Label(ci,text="📷  Live Camera Feed",fg=FG_DIM,bg=BG_CARD,font=('Segoe UI',9,'bold'),anchor='w').pack(fill='x',padx=10,pady=(8,0))
        self._cam_lbl=tk.Label(ci,bg='#0a0f16',text="Initialising camera…",fg=FG_DIM,font=('Segoe UI',11))
        self._cam_lbl.pack(fill='both',expand=True,padx=6,pady=6)
        ctrl=tk.Frame(ci,bg=BG_CARD); ctrl.pack(fill='x',padx=6,pady=(0,8))
        self._pause_btn=self._btn(ctrl,"⏸  Pause",self._toggle_camera,bg='#444c56')
        self._pause_btn.pack(side='left',padx=6)
        self._btn(ctrl,"⌨️  Manual Enter",self._manual_entry_dialog,bg=BLUE).pack(side='left',padx=4)

        right=tk.Frame(tab,bg=BG,width=360); right.pack(side='right',fill='y',padx=(4,8),pady=8)
        right.pack_propagate(False)
        bc=tk.Frame(right,bg=BORDER,padx=1,pady=1); bc.pack(fill='x',pady=(0,6))
        bi=tk.Frame(bc,bg=BG_CARD); bi.pack(fill='both',expand=True)
        self._badge_lbl=tk.Label(bi,text="● READY",fg=GREEN,bg=BG_CARD,font=('Segoe UI',15,'bold'))
        self._badge_lbl.pack(pady=8)

        ic=tk.Frame(right,bg=BORDER,padx=1,pady=1); ic.pack(fill='x',pady=(0,6))
        ii=tk.Frame(ic,bg=BG_CARD); ii.pack(fill='both',expand=True)
        tk.Label(ii,text="📄  Scan Result",fg=FG_DIM,bg=BG_CARD,font=('Segoe UI',9,'bold'),anchor='w').pack(fill='x',padx=10,pady=(8,0))
        self._info_vars={}
        for label_text,key in [('Book ID','book_id'),('Title','title'),('Author','author'),
                                ('Availability','avail'),(None,None),
                                ('Student Name','student'),('Email','email'),('Phone','phone'),
                                (None,None),('Due Date','due'),('Action','action')]:
            if key is None:
                tk.Frame(ii,bg='#2d333b',height=1).pack(fill='x',padx=10,pady=4)
                continue
            row=tk.Frame(ii,bg=BG_CARD); row.pack(fill='x',padx=10,pady=2)
            tk.Label(row,text=f"{label_text}:",fg=FG_DIM,bg=BG_CARD,font=('Segoe UI',9),width=13,anchor='w').pack(side='left')
            var=tk.StringVar(value='—')
            tk.Label(row,textvariable=var,fg=FG,bg=BG_CARD,font=('Segoe UI',9,'bold'),anchor='w',wraplength=180).pack(side='left',fill='x',expand=True)
            self._info_vars[key]=var
        tk.Frame(ii,bg=BG_CARD,height=6).pack()

        rc=tk.Frame(right,bg=BORDER,padx=1,pady=1); rc.pack(fill='both',expand=True)
        ri=tk.Frame(rc,bg=BG_CARD); ri.pack(fill='both',expand=True)
        tk.Label(ri,text="🕑  Recent Scans",fg=FG_DIM,bg=BG_CARD,font=('Segoe UI',9,'bold'),anchor='w').pack(fill='x',padx=10,pady=(8,0))
        self._recent_lb=tk.Listbox(ri,bg=BG_MID,fg=FG,font=('Consolas',8),relief='flat',
                                    selectbackground=ACCENT,borderwidth=0,highlightthickness=0)
        self._recent_lb.pack(fill='both',expand=True,padx=6,pady=6)

    # ══ BOOKS TAB ════════════════════════════════════════════════════════════
    def _build_books_tab(self):
        tab=self._tab_books
        tb=tk.Frame(tab,bg=BG_MID,height=48); tb.pack(fill='x',padx=6,pady=(6,0)); tb.pack_propagate(False)
        for label,cmd,color in [("➕ Add Book",self._add_book_dialog,ACCENT),("✏️ Edit",self._edit_book_dialog,'#444c56'),
                                  ("🗑️ Delete",self._delete_book,'#b22222'),("📤 Gen QR",self._generate_qr,'#1f6feb'),
                                  ("🖨️ Print",self._open_qr_file,'#388bfd'),("🔄 Refresh",self._refresh_books,'#1a7f37')]:
            self._btn(tb,label,cmd,bg=color).pack(side='left',padx=4,pady=8)
        sf=tk.Frame(tb,bg=BG_MID); sf.pack(side='right',padx=10)
        tk.Label(sf,text="🔍",bg=BG_MID,fg=FG_DIM,font=('Segoe UI',11)).pack(side='left')
        self._books_search_var=tk.StringVar()
        self._books_search_var.trace_add('write',lambda *_:self._refresh_books())
        tk.Entry(sf,textvariable=self._books_search_var,width=22,bg=BG_CARD,fg=FG,
                 insertbackground=FG,relief='flat',font=('Segoe UI',10),bd=4).pack(side='left',padx=5)
        split=tk.Frame(tab,bg=BG); split.pack(fill='both',expand=True,padx=6,pady=6)
        tf=tk.Frame(split,bg=BG); tf.pack(side='left',fill='both',expand=True)
        cols=('book_id','title','author','isbn','genre','qty','avail','added')
        hdrs=('Book ID','Title','Author','ISBN','Genre','Qty','Avail','Added')
        wids=(70,200,150,130,100,40,40,100)
        self._books_tree=ttk.Treeview(tf,columns=cols,show='headings',selectmode='browse')
        for col,hdr,w in zip(cols,hdrs,wids):
            self._books_tree.heading(col,text=hdr); self._books_tree.column(col,width=w,minwidth=30)
        vsb=ttk.Scrollbar(tf,orient='vertical',command=self._books_tree.yview)
        vsb.pack(side='right',fill='y'); self._books_tree.configure(yscrollcommand=vsb.set)
        self._books_tree.pack(fill='both',expand=True)
        self._books_tree.tag_configure('avail',foreground=FG); self._books_tree.tag_configure('unavail',foreground=ORANGE)
        self._books_tree.bind('<<TreeviewSelect>>',self._on_book_select)
        self._books_tree.bind('<Double-1>',lambda _:self._edit_book_dialog())
        qp=tk.Frame(split,bg=BG_MID,width=200); qp.pack(side='right',fill='y',padx=(6,0)); qp.pack_propagate(False)
        tk.Label(qp,text="QR Preview",fg=FG_DIM,bg=BG_MID,font=('Segoe UI',9)).pack(pady=(12,4))
        self._qr_preview_lbl=tk.Label(qp,bg=BG_MID,fg=FG_DIM,text="Select a book\nto preview QR",font=('Segoe UI',9))
        self._qr_preview_lbl.pack(padx=8,pady=4)
        self._refresh_books()

    # ══ SEARCH TAB ═══════════════════════════════════════════════════════════
    def _build_search_tab(self):
        tab=self._tab_search
        top=tk.Frame(tab,bg=BG_CARD,pady=20); top.pack(fill='x',padx=20,pady=(20,0))
        tk.Label(top,text="🔍  Search Library",font=('Segoe UI',18,'bold'),fg=FG,bg=BG_CARD).pack()
        tk.Label(top,text="Type book name, author, ID or genre to check availability",
                 font=('Segoe UI',10),fg=FG_DIM,bg=BG_CARD).pack(pady=(4,12))
        sr=tk.Frame(top,bg=BG_CARD); sr.pack()
        self._search_var=tk.StringVar()
        self._search_var.trace_add('write',lambda *_:self._do_search())
        se=tk.Entry(sr,textvariable=self._search_var,font=('Segoe UI',14),bg=BG_MID,fg=FG,
                    insertbackground=FG,relief='flat',width=36,bd=8)
        se.pack(side='left',padx=(0,8)); se.focus()
        self._btn(sr,"Search",self._do_search,bg=ACCENT).pack(side='left')
        self._btn(sr,"Clear",lambda:self._search_var.set(''),bg='#444c56').pack(side='left',padx=6)
        self._search_stats=tk.Label(top,text="",font=('Segoe UI',10),fg=FG_DIM,bg=BG_CARD)
        self._search_stats.pack(pady=(8,0))
        rf=tk.Frame(tab,bg=BG); rf.pack(fill='both',expand=True,padx=20,pady=10)
        cols=('book_id','title','author','genre','available','total','status')
        hdrs=('Book ID','Title','Author','Genre','Available','Total','Status')
        wids=(70,260,170,100,80,60,120)
        self._search_tree=ttk.Treeview(rf,columns=cols,show='headings',selectmode='browse')
        for col,hdr,w in zip(cols,hdrs,wids):
            self._search_tree.heading(col,text=hdr); self._search_tree.column(col,width=w,minwidth=40)
        self._search_tree.tag_configure('available',foreground=GREEN)
        self._search_tree.tag_configure('unavailable',foreground=RED)
        self._search_tree.tag_configure('low',foreground=ORANGE)
        vsb=ttk.Scrollbar(rf,orient='vertical',command=self._search_tree.yview)
        vsb.pack(side='right',fill='y'); self._search_tree.configure(yscrollcommand=vsb.set)
        self._search_tree.pack(fill='both',expand=True)
        self._do_search()

    def _do_search(self):
        query=self._search_var.get().strip() if hasattr(self,'_search_var') else ''
        books=self.manager.search_books(query) if query else self.manager.get_all_books()
        for row in self._search_tree.get_children(): self._search_tree.delete(row)
        avail_count=0
        for b in books:
            avail=b['available']; qty=b['quantity']
            if avail==0: status,tag='❌ Not Available','unavailable'
            elif avail==1: status,tag='⚠️ Last Copy','low'
            else: status,tag=f'✅ Available ({avail} copies)','available'; avail_count+=1
            self._search_tree.insert('','end',values=(b['book_id'],b['title'],b['author'],
                b.get('genre',''),avail,qty,status),tags=(tag,))
        self._search_stats.config(text=f"{len(books)} books  •  {avail_count} available"+
                                   (f"  •  '{query}'" if query else ""))

    # ══ DEADLINES TAB ════════════════════════════════════════════════════════
    def _build_deadlines_tab(self):
        tab=self._tab_deadlines
        tb=tk.Frame(tab,bg=BG_MID,height=48); tb.pack(fill='x',padx=6,pady=(6,0)); tb.pack_propagate(False)
        for label,cmd,color in [("🔄 Refresh",self._refresh_deadlines,'#1a7f37'),
                                  ("📧 Send Reminder",self._send_reminder_selected,BLUE),
                                  ("🔃 Check Now",self._run_check_now,'#534AB7')]:
            self._btn(tb,label,cmd,bg=color).pack(side='left',padx=4,pady=8)
        self._deadline_status_lbl=tk.Label(tb,text="",fg=FG_DIM,bg=BG_MID,font=('Segoe UI',9))
        self._deadline_status_lbl.pack(side='right',padx=16)
        leg=tk.Frame(tab,bg=BG); leg.pack(fill='x',padx=8,pady=(6,0))
        for text,color in [("● Overdue",RED),("● Due Tomorrow",ORANGE),("● Due Soon",'#f0e68c'),("● OK",GREEN)]:
            tk.Label(leg,text=text,fg=color,bg=BG,font=('Segoe UI',9)).pack(side='left',padx=14)
        tf=tk.Frame(tab,bg=BG); tf.pack(fill='both',expand=True,padx=6,pady=6)
        cols=('book_id','title','student','email','phone','issue_date','due_date','days_left','fine')
        hdrs=('Book ID','Title','Student','Email','Phone','Issued','Due Date','Days Left','Fine (Rs)')
        wids=(70,170,120,160,100,90,90,80,80)
        self._dl_tree=ttk.Treeview(tf,columns=cols,show='headings',selectmode='browse')
        for col,hdr,w in zip(cols,hdrs,wids):
            self._dl_tree.heading(col,text=hdr); self._dl_tree.column(col,width=w,minwidth=40)
        self._dl_tree.tag_configure('overdue',foreground=RED); self._dl_tree.tag_configure('tomorrow',foreground=ORANGE)
        self._dl_tree.tag_configure('soon',foreground='#f0e68c'); self._dl_tree.tag_configure('ok',foreground=GREEN)
        vsb=ttk.Scrollbar(tf,orient='vertical',command=self._dl_tree.yview)
        vsb.pack(side='right',fill='y'); self._dl_tree.configure(yscrollcommand=vsb.set)
        self._dl_tree.pack(fill='both',expand=True)
        self._dl_records=[]; self._refresh_deadlines()

    def _refresh_deadlines(self):
        records=self.manager.get_active_issues(); self._dl_records=records
        for row in self._dl_tree.get_children(): self._dl_tree.delete(row)
        for r in records:
            days=r.get('days_left'); fine=r.get('fine',0)
            over=r.get('overdue',False); tom=r.get('due_tomorrow',False)
            if days is None: days_str,tag='—','ok'
            elif over: days_str,tag=f"OVERDUE {abs(days)}d",'overdue'
            elif tom: days_str,tag="TOMORROW",'tomorrow'
            elif days<=7: days_str,tag=f"{days} days",'soon'
            else: days_str,tag=f"{days} days",'ok'
            try:
                from datetime import datetime
                issue_fmt=datetime.fromisoformat(r.get('issue_date','')).strftime('%d %b %Y') if r.get('issue_date') else '—'
                due_fmt=datetime.fromisoformat(r.get('due_date','')).strftime('%d %b %Y') if r.get('due_date') else '—'
            except: issue_fmt=r.get('issue_date','')[:10]; due_fmt=r.get('due_date','')[:10]
            self._dl_tree.insert('','end',values=(r.get('book_id',''),r.get('title',''),
                r.get('student_name','—'),r.get('student_email','—'),r.get('student_phone','—'),
                issue_fmt,due_fmt,days_str,f"Rs {fine:.0f}" if fine>0 else '—'),tags=(tag,))
        self._deadline_status_lbl.config(
            text=f"Active: {len(records)}  |  Overdue: {sum(1 for r in records if r.get('overdue'))}")

    def _send_reminder_selected(self):
        sel=self._dl_tree.selection()
        if not sel: messagebox.showwarning("Select Row","Select an issued book first.",parent=self.root); return
        idx=self._dl_tree.index(sel[0])
        if idx>=len(self._dl_records): return
        record=self._dl_records[idx]
        email=record.get('student_email','').strip(); phone=record.get('student_phone','').strip()
        if not email and not phone: messagebox.showwarning("No Contact","No email or phone saved.",parent=self.root); return
        def cb(ok,msg): self.root.after(0,lambda:messagebox.showinfo("Result",msg,parent=self.root))
        self.manager.send_reminder_manually(record,cb); self._set_status("Sending reminder…")

    def _run_check_now(self):
        self.manager.run_deadline_check(); self._set_status("Deadline check running…")

    def _on_checker_status(self,msg):
        self.root.after(0,lambda:self._set_status(msg))
        self.root.after(0,self._refresh_deadlines)

    # ══ HISTORY TAB ══════════════════════════════════════════════════════════
    def _build_history_tab(self):
        tab=self._tab_history
        tb=tk.Frame(tab,bg=BG_MID,height=48); tb.pack(fill='x',padx=6,pady=(6,0)); tb.pack_propagate(False)
        self._btn(tb,"🔄 Refresh",self._refresh_history,bg='#1a7f37').pack(side='left',padx=6,pady=8)
        tk.Label(tb,text="Filter:",fg=FG_DIM,bg=BG_MID,font=('Segoe UI',9)).pack(side='left',padx=(20,4))
        self._hist_filter_var=tk.StringVar()
        tk.Entry(tb,textvariable=self._hist_filter_var,width=12,bg=BG_CARD,fg=FG,
                 insertbackground=FG,relief='flat',font=('Segoe UI',10)).pack(side='left')
        self._btn(tb,"Apply",self._refresh_history,bg='#444c56').pack(side='left',padx=6)
        hf=tk.Frame(tab,bg=BG); hf.pack(fill='both',expand=True,padx=6,pady=6)
        cols=('id','book_id','action','student','email','phone','due_date','fine','timestamp')
        hdrs=('ID','Book ID','Action','Student','Email','Phone','Due Date','Fine','Timestamp')
        wids=(40,70,80,130,150,100,90,70,160)
        self._hist_tree=ttk.Treeview(hf,columns=cols,show='headings',selectmode='browse')
        for col,hdr,w in zip(cols,hdrs,wids):
            self._hist_tree.heading(col,text=hdr); self._hist_tree.column(col,width=w)
        self._hist_tree.tag_configure('ISSUED',foreground='#ffa657')
        self._hist_tree.tag_configure('RETURNED',foreground=GREEN)
        vsb=ttk.Scrollbar(hf,orient='vertical',command=self._hist_tree.yview)
        vsb.pack(side='right',fill='y'); self._hist_tree.configure(yscrollcommand=vsb.set)
        self._hist_tree.pack(fill='both',expand=True); self._refresh_history()

    def _refresh_history(self):
        filt=self._hist_filter_var.get().strip() if hasattr(self,'_hist_filter_var') else ''
        history=self.manager.get_history(filt or None)
        for row in self._hist_tree.get_children(): self._hist_tree.delete(row)
        for h in history:
            fine=h.get('fine_amount',0) or 0
            self._hist_tree.insert('','end',values=(h['id'],h['book_id'],h['action'],
                h.get('student_name',''),h.get('student_email',''),h.get('student_phone',''),
                str(h.get('due_date',''))[:10],f"Rs {fine:.0f}" if fine>0 else '—',
                str(h['timestamp'])[:19]),tags=(h['action'],))

    # ══ SETTINGS TAB — CLEAN & SIMPLE ════════════════════════════════════════
    def _build_settings_tab(self):
        tab = self._tab_settings

        # Main scrollable container
        main = tk.Frame(tab, bg=BG)
        main.pack(fill='both', expand=True)

        # Inner padded frame
        inner = tk.Frame(main, bg=BG)
        inner.pack(fill='both', expand=True, padx=40, pady=20)

        # ── EMAIL SECTION ─────────────────────────────────────────────────────
        tk.Label(inner, text="📧  Email Settings  (Gmail SMTP)",
                 fg=FG, bg=BG, font=('Segoe UI', 13, 'bold')).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(0, 8))

        email_frame = tk.Frame(inner, bg=BG_CARD, relief='flat', padx=20, pady=16)
        email_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(0, 20))
        inner.columnconfigure(0, weight=1)

        tk.Label(email_frame,
                 text="Students get email: confirmation when issued, reminder 1 day before due date, fine notice if overdue.",
                 fg=FG_DIM, bg=BG_CARD, font=('Segoe UI', 9)).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(0, 12))

        tk.Label(email_frame, text="Gmail Address:", fg=FG_DIM, bg=BG_CARD,
                 font=('Segoe UI', 10), width=18, anchor='w').grid(row=1, column=0, sticky='w', pady=6)
        self._gmail_entry = tk.Entry(email_frame, bg=BG_MID, fg=FG, insertbackground=FG,
                                      relief='flat', font=('Segoe UI', 11), width=40)
        self._gmail_entry.grid(row=1, column=1, sticky='ew', padx=(8, 0), pady=6, ipady=4)
        try:
            self._gmail_entry.insert(0, self.manager.get_setting('email_sender', ''))
        except Exception:
            pass

        tk.Label(email_frame, text="App Password:", fg=FG_DIM, bg=BG_CARD,
                 font=('Segoe UI', 10), width=18, anchor='w').grid(row=2, column=0, sticky='w', pady=6)
        self._apppwd_entry = tk.Entry(email_frame, bg=BG_MID, fg=FG, insertbackground=FG,
                                       relief='flat', font=('Segoe UI', 11), width=40, show='*')
        self._apppwd_entry.grid(row=2, column=1, sticky='ew', padx=(8, 0), pady=6, ipady=4)
        try:
            self._apppwd_entry.insert(0, self.manager.get_setting('email_password', ''))
        except Exception:
            pass

        tk.Label(email_frame,
                 text="How to get App Password: myaccount.google.com → Security → 2-Step Verification → App Passwords → Generate",
                 fg='#555', bg=BG_CARD, font=('Segoe UI', 8)).grid(
            row=3, column=0, columnspan=3, sticky='w', pady=(4, 8))

        bf_email = tk.Frame(email_frame, bg=BG_CARD)
        bf_email.grid(row=4, column=0, columnspan=3, sticky='w', pady=(0, 6))
        self._btn(bf_email, "💾  Save Email Settings", self._save_email, bg=ACCENT).pack(side='left', padx=(0, 10))
        self._btn(bf_email, "🔌  Test Connection",     self._test_email, bg=BLUE).pack(side='left')

        self._email_status = tk.Label(email_frame, text="", fg=GREEN, bg=BG_CARD, font=('Segoe UI', 9))
        self._email_status.grid(row=5, column=0, columnspan=3, sticky='w')

        # ── SMS SECTION ───────────────────────────────────────────────────────
        tk.Label(inner, text="📱  SMS Settings  (Fast2SMS — India, FREE)",
                 fg=FG, bg=BG, font=('Segoe UI', 13, 'bold')).grid(
            row=2, column=0, columnspan=3, sticky='w', pady=(0, 8))

        sms_frame = tk.Frame(inner, bg=BG_CARD, relief='flat', padx=20, pady=16)
        sms_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=(0, 20))

        tk.Label(sms_frame,
                 text="Students get SMS on mobile: confirmation, reminder before due date, overdue fine notice.\nSign up FREE at fast2sms.com — Rs 50 free credits on signup!",
                 fg=FG_DIM, bg=BG_CARD, font=('Segoe UI', 9), justify='left').grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(0, 12))

        tk.Label(sms_frame, text="Fast2SMS API Key:", fg=FG_DIM, bg=BG_CARD,
                 font=('Segoe UI', 10), width=18, anchor='w').grid(row=1, column=0, sticky='w', pady=6)
        self._sms_api_entry = tk.Entry(sms_frame, bg=BG_MID, fg=FG, insertbackground=FG,
                                        relief='flat', font=('Segoe UI', 11), width=36, show='*')
        self._sms_api_entry.grid(row=1, column=1, sticky='ew', padx=(8, 0), pady=6, ipady=4)
        try:
            self._sms_api_entry.insert(0, self.manager.get_setting('sms_api_key', ''))
        except Exception:
            pass
        self._btn(sms_frame, "👁", self._toggle_sms_show, bg='#444c56').grid(row=1, column=2, padx=(6, 0))

        tk.Label(sms_frame, text="Test Phone Number:", fg=FG_DIM, bg=BG_CARD,
                 font=('Segoe UI', 10), width=18, anchor='w').grid(row=2, column=0, sticky='w', pady=6)
        self._test_phone = tk.Entry(sms_frame, bg=BG_MID, fg=FG, insertbackground=FG,
                                     relief='flat', font=('Segoe UI', 11), width=24)
        self._test_phone.grid(row=2, column=1, sticky='w', padx=(8, 0), pady=6, ipady=4)
        self._test_phone.insert(0, '9876543210')

        tk.Label(sms_frame,
                 text="How to get Fast2SMS API Key:\n"
                      "  1. Go to fast2sms.com  →  Sign Up (FREE)\n"
                      "  2. Dashboard  →  Dev API  →  Copy API Key\n"
                      "  3. Paste above  →  Save SMS Settings",
                 fg='#555', bg=BG_CARD, font=('Segoe UI', 8), justify='left').grid(
            row=3, column=0, columnspan=3, sticky='w', pady=(4, 8))

        bf_sms = tk.Frame(sms_frame, bg=BG_CARD)
        bf_sms.grid(row=4, column=0, columnspan=3, sticky='w', pady=(0, 6))
        self._btn(bf_sms, "💾  Save SMS Settings", self._save_sms,  bg='#1a7f37').pack(side='left', padx=(0, 10))
        self._btn(bf_sms, "📱  Send Test SMS",      self._test_sms,  bg='#534AB7').pack(side='left')

        self._sms_status = tk.Label(sms_frame, text="", fg=GREEN, bg=BG_CARD, font=('Segoe UI', 9))
        self._sms_status.grid(row=5, column=0, columnspan=3, sticky='w')

        # ── LIBRARY SECTION ───────────────────────────────────────────────────
        tk.Label(inner, text="📚  Library Settings",
                 fg=FG, bg=BG, font=('Segoe UI', 13, 'bold')).grid(
            row=4, column=0, columnspan=3, sticky='w', pady=(0, 8))

        lib_frame = tk.Frame(inner, bg=BG_CARD, relief='flat', padx=20, pady=16)
        lib_frame.grid(row=5, column=0, columnspan=3, sticky='ew', pady=(0, 20))

        self._lib_entries = {}
        lib_fields = [
            (0, "Loan Period (days):", 'loan_days',   '30', "Days student can keep a book"),
            (1, "Fine Per Day (Rs):",  'fine_per_day', '5', "Fine charged per day after due date"),
        ]
        for row_idx, lbl_text, key, default, hint in lib_fields:
            tk.Label(lib_frame, text=lbl_text, fg=FG_DIM, bg=BG_CARD,
                     font=('Segoe UI', 10), width=20, anchor='w').grid(
                row=row_idx, column=0, sticky='w', pady=8)
            e = tk.Entry(lib_frame, bg=BG_MID, fg=FG, insertbackground=FG,
                         relief='flat', font=('Segoe UI', 11), width=14)
            e.grid(row=row_idx, column=1, sticky='w', padx=(8, 0), pady=8, ipady=4)
            try:
                e.insert(0, self.manager.get_setting(key, default))
            except Exception:
                e.insert(0, default)
            tk.Label(lib_frame, text=hint, fg='#555', bg=BG_CARD,
                     font=('Segoe UI', 8)).grid(row=row_idx, column=2, sticky='w', padx=12)
            self._lib_entries[key] = e

        bf_lib = tk.Frame(lib_frame, bg=BG_CARD)
        bf_lib.grid(row=2, column=0, columnspan=3, sticky='w', pady=(8, 0))
        self._btn(bf_lib, "💾  Save Library Settings", self._save_lib, bg='#1a7f37').pack(side='left')
        self._lib_status = tk.Label(lib_frame, text="", fg=GREEN, bg=BG_CARD, font=('Segoe UI', 9))
        self._lib_status.grid(row=3, column=0, columnspan=3, sticky='w', pady=(6, 0))

    # ── Settings Save/Test actions ────────────────────────────────────────────
    def _save_email(self):
        try:
            email = self._gmail_entry.get().strip()
            pwd   = self._apppwd_entry.get().strip()
            self.manager.save_email_settings(email, pwd)
            self._email_status.config(text="✅  Email settings saved!", fg=GREEN)
        except Exception as e:
            self._email_status.config(text=f"❌  {e}", fg=RED)

    def _test_email(self):
        self._email_status.config(text="Testing connection…", fg=FG_DIM)
        self.root.update_idletasks()
        try:
            ok, msg = self.manager.test_email()
            self._email_status.config(text=("✅  " if ok else "❌  ") + msg,
                                       fg=GREEN if ok else RED)
        except Exception as e:
            self._email_status.config(text=f"❌  {e}", fg=RED)

    def _save_sms(self):
        try:
            api_key = self._sms_api_entry.get().strip()
            try:
                self.manager.save_sms_settings(api_key)
            except AttributeError:
                self.manager.set_setting('sms_api_key', api_key)
            self._sms_status.config(text="✅  SMS API key saved!", fg=GREEN)
        except Exception as e:
            self._sms_status.config(text=f"❌  {e}", fg=RED)

    def _test_sms(self):
        api_key = self._sms_api_entry.get().strip()
        if not api_key:
            self._sms_status.config(text="❌  Enter API key first!", fg=RED); return
        self._save_sms()
        phone = self._test_phone.get().strip()
        self._sms_status.config(text="Sending test SMS…", fg=FG_DIM)
        self.root.update_idletasks()
        def cb(ok, msg):
            self.root.after(0, lambda: self._sms_status.config(
                text=("✅  " if ok else "❌  ") + msg, fg=GREEN if ok else RED))
        try:
            self.manager.test_sms(phone, cb)
        except AttributeError:
            self._sms_status.config(text="❌  Update library_manager.py too!", fg=RED)

    def _toggle_sms_show(self):
        cur = self._sms_api_entry.cget('show')
        self._sms_api_entry.config(show='' if cur == '*' else '*')

    def _save_lib(self):
        try:
            for key, entry in self._lib_entries.items():
                val = entry.get().strip()
                if val:
                    self.manager.set_setting(key, val)
            self._lib_status.config(text="✅  Library settings saved!", fg=GREEN)
        except Exception as e:
            self._lib_status.config(text=f"❌  {e}", fg=RED)

    # ══ CAMERA ═══════════════════════════════════════════════════════════════
    def _start_camera(self):
        if not CV2_OK:
            self._cam_lbl.config(text="OpenCV / Pillow not installed.\npip install opencv-python Pillow",fg=ORANGE); return
        try:
            self.scanner.start(); self.camera_active=True; self._update_camera()
        except RuntimeError as e:
            self._cam_lbl.config(text=f"Camera Error:\n{e}",fg=ORANGE)

    def _update_camera(self):
        if not self.camera_active: return
        frame=self.scanner.get_frame()
        if frame is not None and CV2_OK:
            rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            h,w=rgb.shape[:2]; scale=min(820/w,480/h)
            rgb=cv2.resize(rgb,(int(w*scale),int(h*scale)))
            img=Image.fromarray(rgb); imgtk=ImageTk.PhotoImage(image=img)
            self._cam_lbl.imgtk=imgtk; self._cam_lbl.config(image=imgtk,text='')
        self._cam_after_id=self.root.after(33,self._update_camera)

    def _toggle_camera(self):
        self.camera_active=not self.camera_active
        if self.camera_active:
            self._pause_btn.config(text="⏸  Pause"); self._update_camera()
        else:
            self._pause_btn.config(text="▶  Resume")
            if self._cam_after_id: self.root.after_cancel(self._cam_after_id)

    # ══ SCAN ═════════════════════════════════════════════════════════════════
    def _on_qr_scanned(self,qr_data):
        self.root.after(0,lambda d=qr_data:self._ask_student_info(d))

    def _ask_student_info(self,qr_data):
        book=self.manager.get_book(qr_data)
        if not book or book['available']==0:
            self._process_scan(qr_data,'','','',''); return
        dlg=tk.Toplevel(self.root); dlg.title("Student Details")
        dlg.geometry("420x320"); dlg.configure(bg=BG); dlg.grab_set(); dlg.resizable(False,False)
        hdr=tk.Frame(dlg,bg=ACCENT,height=50); hdr.pack(fill='x'); hdr.pack_propagate(False)
        tk.Label(hdr,text=f"📖  Issuing: {book['title'][:38]}",
                 font=('Segoe UI',11,'bold'),fg='white',bg=ACCENT).pack(padx=16,pady=12,anchor='w')
        tk.Label(dlg,text="Fill student details — Email/Phone needed for reminders:",
                 font=('Segoe UI',9),fg=FG_DIM,bg=BG).pack(padx=20,pady=(12,4),anchor='w')
        form=tk.Frame(dlg,bg=BG); form.pack(fill='x',padx=20); form.columnconfigure(1,weight=1)
        fields=[('Student Name *','name'),('Student ID','sid'),('Email *','email'),('Phone *','phone')]
        entries={}
        for i,(lbl,key) in enumerate(fields):
            tk.Label(form,text=lbl,fg=FG_DIM,bg=BG,font=('Segoe UI',9),anchor='w').grid(row=i,column=0,sticky='w',pady=6)
            e=tk.Entry(form,bg=BG_CARD,fg=FG,insertbackground=FG,relief='flat',font=('Segoe UI',10),bd=5)
            e.grid(row=i,column=1,sticky='ew',padx=(12,0),pady=6); entries[key]=e
        entries['name'].focus()
        loan=self.manager.get_setting('loan_days','30')
        tk.Label(dlg,text=f"Loan: {loan} days  |  Email + SMS sent automatically",
                 fg='#444c56',bg=BG,font=('Segoe UI',8)).pack(padx=20,pady=(4,0),anchor='w')
        def _submit():
            # ✅ FIX: Read values FIRST before destroying dialog
            # After dlg.destroy(), entry widgets are gone — .get() would fail!
            name  = entries['name'].get().strip()
            sid   = entries['sid'].get().strip()
            email = entries['email'].get().strip()
            phone = entries['phone'].get().strip()
            dlg.destroy()
            self._process_scan(qr_data, name, sid, email, phone)
        def _skip():
            dlg.destroy(); self._process_scan(qr_data,'','','','')
        bf=tk.Frame(dlg,bg=BG); bf.pack(pady=12)
        self._btn(bf,"✅  Issue Book",_submit,bg=GREEN).pack(side='left',padx=8)
        self._btn(bf,"Skip",_skip,bg='#444c56').pack(side='left',padx=8)
        dlg.bind('<Return>',lambda _:_submit())

    def _process_scan(self,qr_data,student_name,student_id,student_email,student_phone):
        event=self.manager.process_qr_scan(qr_data,student_name,student_id,student_email,student_phone)
        self._update_scan_panel(event); self._refresh_books()
        self._refresh_history(); self._refresh_deadlines(); self._do_search()

    def _on_library_event(self,event): pass

    def _update_scan_panel(self,event):
        book=event.get('book'); etype=event.get('type','INVALID'); msg=event.get('message','')
        student_name=event.get('student_name',''); student_email=event.get('student_email','')
        student_phone=event.get('student_phone',''); due_date=event.get('due_date','')
        if book:
            self._info_vars['book_id'].set(str(book.get('book_id','—')))
            self._info_vars['title'].set(str(book.get('title','—'))[:40])
            self._info_vars['author'].set(str(book.get('author','—'))[:40])
            self._info_vars['avail'].set(f"{book.get('available',0)} of {book.get('quantity',1)} copies available")
        else:
            for k in ('book_id','title','author','avail'): self._info_vars[k].set('—')
        self._info_vars['student'].set(student_name or '—')
        self._info_vars['email'].set(student_email or '—')
        self._info_vars['phone'].set(student_phone or '—')
        self._info_vars['due'].set(due_date or '—')
        cfg={'ISSUE':('✅  BOOK ISSUED',GREEN),'RETURN':('↩️  BOOK RETURNED',BLUE),
             'INVALID':('❌  INVALID QR',RED),'ERROR':('⚠️  ERROR',ORANGE)}
        badge_text,badge_color=cfg.get(etype,('● READY',GREEN))
        self._info_vars['action'].set(badge_text); self._badge_lbl.config(text=badge_text,fg=badge_color)
        ts=time.strftime('%H:%M:%S')
        name_part=f" | {student_name}" if student_name else ""
        self._recent_lb.insert(0,f"[{ts}]  {etype:<8}  {book.get('book_id','?') if book else '?'}{name_part}")
        if self._recent_lb.size()>30: self._recent_lb.delete(30)
        self._set_status(msg)
        self.root.after(5000,lambda:self._badge_lbl.config(text='● READY',fg=GREEN))

    def _manual_entry_dialog(self):
        dlg=tk.Toplevel(self.root); dlg.title("Manual Entry"); dlg.geometry("340x140")
        dlg.configure(bg=BG); dlg.grab_set(); dlg.resizable(False,False)
        tk.Label(dlg,text="Enter Book ID (e.g. BK001):",fg=FG,bg=BG,font=('Segoe UI',11)).pack(pady=16)
        var=tk.StringVar()
        e=tk.Entry(dlg,textvariable=var,bg=BG_CARD,fg=FG,insertbackground=FG,font=('Segoe UI',12),relief='flat',width=20)
        e.pack(pady=4); e.focus()
        def submit():
            v=var.get().strip()
            if v: dlg.destroy(); self._ask_student_info(v)
        e.bind('<Return>',lambda _:submit())
        self._btn(dlg,"Scan",submit,bg=ACCENT).pack(pady=10)

    # ══ BOOKS CRUD ═══════════════════════════════════════════════════════════
    def _refresh_books(self):
        q=self._books_search_var.get().strip() if hasattr(self,'_books_search_var') else ''
        books=self.manager.search_books(q) if q else self.manager.get_all_books()
        for row in self._books_tree.get_children(): self._books_tree.delete(row)
        for b in books:
            tag='avail' if b['available']>0 else 'unavail'
            self._books_tree.insert('','end',values=(b['book_id'],b['title'],b['author'],
                b.get('isbn',''),b.get('genre',''),b['quantity'],b['available'],
                str(b.get('added_date',''))[:10]),tags=(tag,))

    def _on_book_select(self,_=None):
        sel=self._books_tree.selection()
        if not sel: return
        self.selected_book_id=self._books_tree.item(sel[0])['values'][0]
        self._load_qr_preview(self.selected_book_id)

    def _load_qr_preview(self,book_id):
        if not CV2_OK: return
        path=self.manager.qr_gen.get_qr_path(book_id)
        if path:
            try:
                img=Image.open(path).resize((180,180)); imgtk=ImageTk.PhotoImage(img)
                self._qr_preview_lbl.imgtk=imgtk; self._qr_preview_lbl.config(image=imgtk,text=''); return
            except Exception: pass
        self._qr_preview_lbl.config(image='',text=f"No QR for {book_id}")

    def _add_book_dialog(self): self._book_form(mode='add')

    def _edit_book_dialog(self):
        if not self.selected_book_id: messagebox.showwarning("No Selection","Select a book first.",parent=self.root); return
        self._book_form(mode='edit',book_id=self.selected_book_id)

    def _book_form(self,mode='add',book_id=None):
        dlg=tk.Toplevel(self.root); dlg.title("Add Book" if mode=='add' else "Edit Book")
        dlg.geometry("460x520"); dlg.configure(bg=BG); dlg.grab_set(); dlg.resizable(False,False)
        tk.Label(dlg,text="Add New Book" if mode=='add' else "Edit Book",
                 font=('Segoe UI',14,'bold'),fg=ACCENT,bg=BG).pack(pady=14)
        form=tk.Frame(dlg,bg=BG); form.pack(padx=30,fill='x'); form.columnconfigure(1,weight=1)
        fields=['Book ID','Title','Author','ISBN','Genre','Quantity']; entries={}
        for i,f in enumerate(fields):
            tk.Label(form,text=f"{f}:",fg=FG_DIM,bg=BG,font=('Segoe UI',9),anchor='w').grid(row=i,column=0,sticky='w',pady=5)
            e=tk.Entry(form,bg=BG_CARD,fg=FG,insertbackground=FG,relief='flat',font=('Segoe UI',10),bd=5)
            e.grid(row=i,column=1,sticky='ew',padx=(10,0),pady=5); entries[f]=e

        # ── PDF attachment (public domain / free books only) ────────────────
        pdf_path_var = tk.StringVar(value='')
        pdf_row = tk.Frame(form, bg=BG)
        pdf_row.grid(row=len(fields), column=0, columnspan=2, sticky='ew', pady=(10, 2))
        tk.Label(pdf_row, text="PDF (optional):", fg=FG_DIM, bg=BG,
                 font=('Segoe UI', 9), anchor='w').pack(side='left')
        pdf_lbl = tk.Label(pdf_row, text="No file selected", fg=FG, bg=BG,
                            font=('Segoe UI', 8), anchor='w')
        pdf_lbl.pack(side='left', padx=8, fill='x', expand=True)

        def _browse_pdf():
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="Select PDF (public domain / free books only)",
                filetypes=[("PDF files", "*.pdf")]
            )
            if path:
                pdf_path_var.set(path)
                pdf_lbl.config(text=os.path.basename(path), fg=GREEN)

        self._btn(pdf_row, "📁 Browse", _browse_pdf, bg='#1f6feb').pack(side='right')

        tk.Label(form,
                 text="⚠️ Only attach PDFs you have legal rights to share\n"
                      "(public domain, NCERT, open-source, or your own notes).\n"
                      "PDF gets emailed to student when book is issued.",
                 fg='#854F0B', bg=BG, font=('Segoe UI', 8), justify='left').grid(
            row=len(fields)+1, column=0, columnspan=2, sticky='w', pady=(2, 8))

        if mode=='edit' and book_id:
            book=self.manager.get_book(book_id)
            if book:
                entries['Book ID'].insert(0,book['book_id']); entries['Book ID'].config(state='disabled')
                entries['Title'].insert(0,book['title']); entries['Author'].insert(0,book['author'])
                entries['ISBN'].insert(0,book.get('isbn','')); entries['Genre'].insert(0,book.get('genre',''))
                entries['Quantity'].insert(0,str(book.get('quantity',1)))
                existing_pdf = book.get('pdf_path', '')
                if existing_pdf and os.path.isfile(existing_pdf):
                    pdf_path_var.set(existing_pdf)
                    pdf_lbl.config(text=os.path.basename(existing_pdf), fg=GREEN)
        else:
            entries['Book ID'].insert(0,self.manager.get_next_book_id()); entries['Quantity'].insert(0,'1')
        gen_var=tk.BooleanVar(value=True)
        tk.Checkbutton(form,text="Generate QR automatically",variable=gen_var,
                       bg=BG,fg=FG,selectcolor=BG_CARD,activebackground=BG,
                       font=('Segoe UI',9)).grid(row=len(fields)+2,column=0,columnspan=2,sticky='w',pady=8)
        def _save():
            try: qty=max(1,int(entries['Quantity'].get() or '1'))
            except ValueError: qty=1
            pdf_path = pdf_path_var.get().strip()
            if mode=='add':
                ok,msg=self.manager.add_book(entries['Book ID'].get().strip(),entries['Title'].get().strip(),
                    entries['Author'].get().strip(),entries['ISBN'].get().strip(),entries['Genre'].get().strip(),
                    qty,gen_var.get(),pdf_path)
            else:
                ok,msg=self.manager.update_book(book_id,entries['Title'].get().strip(),
                    entries['Author'].get().strip(),entries['ISBN'].get().strip(),entries['Genre'].get().strip(),
                    qty,pdf_path)
            if ok: dlg.destroy(); self._refresh_books(); self._do_search(); self._set_status(msg)
            else: messagebox.showerror("Error",msg,parent=dlg)
        bf=tk.Frame(dlg,bg=BG); bf.pack(pady=14)
        self._btn(bf,"💾 Save",_save,bg=ACCENT).pack(side='left',padx=8)
        self._btn(bf,"✖ Cancel",dlg.destroy,bg='#444c56').pack(side='left',padx=8)

    def _delete_book(self):
        if not self.selected_book_id: messagebox.showwarning("No Selection","Select a book first.",parent=self.root); return
        book=self.manager.get_book(self.selected_book_id)
        if not book: return
        if not messagebox.askyesno("Confirm Delete",f"Delete '{book['title']}'?",parent=self.root): return
        ok,msg=self.manager.delete_book(self.selected_book_id); self._set_status(msg)
        if ok:
            self.selected_book_id=None
            self._qr_preview_lbl.config(image='',text="Select a book\nto preview QR")
            self._refresh_books(); self._do_search()

    def _generate_qr(self):
        if not self.selected_book_id: messagebox.showwarning("No Selection","Select a book first.",parent=self.root); return
        path,msg=self.manager.generate_qr_for_book(self.selected_book_id); self._set_status(msg)
        if path:
            self._load_qr_preview(self.selected_book_id)
            messagebox.showinfo("QR Generated",f"{msg}\n\nSaved to:\n{path}",parent=self.root)

    def _open_qr_file(self):
        if not self.selected_book_id: messagebox.showwarning("No Selection","Select a book first.",parent=self.root); return
        path=self.manager.qr_gen.get_qr_path(self.selected_book_id)
        if not path: messagebox.showinfo("No QR","Generate a QR code first.",parent=self.root); return
        if sys.platform=='win32': os.startfile(path)
        elif sys.platform=='darwin': os.system(f"open '{path}'")
        else: os.system(f"xdg-open '{path}'")

    # ══ PICO W ═══════════════════════════════════════════════════════════════
    def _connect_pico_dialog(self):
        ports=self.manager.get_available_ports()
        dlg=tk.Toplevel(self.root); dlg.title("Connect Pico W"); dlg.geometry("400x220")
        dlg.configure(bg=BG); dlg.grab_set()
        tk.Label(dlg,text="Connect Raspberry Pi Pico W",fg=ACCENT,bg=BG,font=('Segoe UI',12,'bold')).pack(pady=14)
        tk.Label(dlg,text="Select port or leave on Auto-detect:",fg=FG_DIM,bg=BG,font=('Segoe UI',9)).pack()
        pv=tk.StringVar(value='Auto-detect')
        choices=['Auto-detect']+[f"{d} — {desc}" for d,desc in ports]
        ttk.Combobox(dlg,textvariable=pv,values=choices,state='readonly',width=40).pack(pady=10)
        rl=tk.Label(dlg,text="",fg=FG_DIM,bg=BG,font=('Segoe UI',9)); rl.pack()
        def _attempt():
            choice=pv.get(); port=None if choice=='Auto-detect' else choice.split(' — ')[0]
            ok,msg=self.manager.connect_pico(port)
            if ok:
                self._conn_dot.config(fg=GREEN); self._conn_lbl.config(text=f" Pico W: {msg}"); rl.config(text=f"✅ {msg}",fg=GREEN)
            else:
                self._conn_dot.config(fg=RED); self._conn_lbl.config(text=" Pico W: Disconnected"); rl.config(text=f"❌ {msg}",fg=RED)
            self._set_status(msg)
        self._btn(dlg,"⚡ Connect",_attempt,bg=ACCENT).pack(pady=8)
        self._btn(dlg,"Close",dlg.destroy,bg='#444c56').pack()

    def on_close(self):
        self.camera_active=False
        if self._cam_after_id: self.root.after_cancel(self._cam_after_id)
        try: self.scanner.stop()
        except Exception: pass
        self.manager.disconnect_pico()
        self.manager.checker.stop()
        self.root.destroy()
