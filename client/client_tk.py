# client/client_tk.py
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import os
import cv2

#Coloque seu IP aqui
SERVER_BASE_URL = os.environ.get('SERVER_BASE_URL', 'http://0.0.0.0:5000')

class VideoClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Cliente de Vídeo — Upload e Histórico')
        self.geometry('900x600')

        self.file_path = tk.StringVar()
        self.filter_var = tk.StringVar(value='grayscale')

        self._build_ui()
        self.refresh_history()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        # Linha de seleção de arquivo
        row1 = ttk.Frame(frm)
        row1.pack(fill=tk.X, pady=6)
        ttk.Label(row1, text='Arquivo de vídeo:').pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.file_path, width=60).pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text='Escolher...', command=self.choose_file).pack(side=tk.LEFT)

        # Linha de filtro + upload
        row2 = ttk.Frame(frm)
        row2.pack(fill=tk.X, pady=6)
        ttk.Label(row2, text='Filtro:').pack(side=tk.LEFT)
        ttk.Combobox(row2, textvariable=self.filter_var, values=['grayscale','pixelate','edges'], width=12, state='readonly').pack(side=tk.LEFT, padx=6)
        ttk.Button(row2, text='Enviar', command=self.upload).pack(side=tk.LEFT, padx=6)
        ttk.Button(row2, text='Atualizar Histórico', command=self.refresh_history).pack(side=tk.LEFT, padx=6)

        # Tabela de histórico
        self.tree = ttk.Treeview(frm, columns=('id','name','filter','fps','res','dur'), show='headings')
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Arquivo')
        self.tree.heading('filter', text='Filtro')
        self.tree.heading('fps', text='FPS')
        self.tree.heading('res', text='Resolução')
        self.tree.heading('dur', text='Duração (s)')
        self.tree.column('id', width=60)
        self.tree.column('name', width=260)
        self.tree.column('filter', width=80)
        self.tree.column('fps', width=60)
        self.tree.column('res', width=120)
        self.tree.column('dur', width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=8)

        # Botões de ação do histórico
        row3 = ttk.Frame(frm)
        row3.pack(fill=tk.X)
        ttk.Button(row3, text='Abrir Original', command=lambda: self.open_selected('original_url')).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text='Abrir Processado', command=lambda: self.open_selected('processed_url')).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text='Preview GIF', command=lambda: self.open_selected('preview_url')).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text='Reproduzir Original (OpenCV)', command=lambda: self.play_selected('original_url')).pack(side=tk.LEFT, padx=4)
        ttk.Button(row3, text='Reproduzir Processado (OpenCV)', command=lambda: self.play_selected('processed_url')).pack(side=tk.LEFT, padx=4)

    def choose_file(self):
        path = filedialog.askopenfilename(filetypes=[('Vídeos','*.mp4 *.mov *.avi *.mkv')])
        if path:
            self.file_path.set(path)

    def upload(self):
        path = self.file_path.get()
        if not os.path.isfile(path):
            messagebox.showerror('Erro', 'Selecione um arquivo válido')
            return
        filt = self.filter_var.get()
        try:
            with open(path, 'rb') as f:
                files = {'file': (os.path.basename(path), f, 'application/octet-stream')}
                data = {'filter': filt}
                r = requests.post(f'{SERVER_BASE_URL}/api/upload', files=files, data=data, timeout=300)
            r.raise_for_status()
            resp = r.json()
            messagebox.showinfo('Sucesso', f"Upload ok! ID: {resp.get('id')}")
            self.refresh_history()
        except Exception as e:
            messagebox.showerror('Falha no upload', str(e))

    def refresh_history(self):
        try:
            r = requests.get(f'{SERVER_BASE_URL}/api/videos?limit=200', timeout=30)
            r.raise_for_status()
            rows = r.json()
            # Limpa tabela
            for i in self.tree.get_children():
                self.tree.delete(i)
            self._rows_cache = rows
            for v in rows:
                res = f"{v.get('width')}x{v.get('height')}"
                self.tree.insert('', tk.END, values=(v.get('id','')[:8], v.get('original_name'), v.get('filter'), f"{v.get('fps',0):.1f}", res, f"{v.get('duration_sec',0):.2f}"))
        except Exception as e:
            messagebox.showerror('Erro', str(e))

    def _get_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Atenção', 'Selecione uma linha do histórico')
            return None
        idx = self.tree.index(sel[0])
        return self._rows_cache[idx]

    def open_selected(self, key):
        import webbrowser
        row = self._get_selected_row()
        if not row:
            return
        url = row.get(key)
        if not url:
            messagebox.showwarning('Atenção', 'URL não disponível')
        else:
            webbrowser.open(url)

    def play_selected(self, key):
        row = self._get_selected_row()
        if not row:
            return
        url = row.get(key)
        if not url:
            messagebox.showwarning('Atenção', 'URL não disponível')
            return
        threading.Thread(target=self._play_stream, args=(url,), daemon=True).start()

    def _play_stream(self, url):
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            messagebox.showerror('Erro', 'Não foi possível abrir o vídeo para reprodução')
            return
        win = 'Reprodução (ESC para sair)'
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            cv2.imshow(win, frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
        cap.release()
        cv2.destroyWindow(win)

if __name__ == '__main__':
    app = VideoClientApp()
    app.mainloop()
