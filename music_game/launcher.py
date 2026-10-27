"""Vietnamese startup controls for camera, video, mode, volume and sound."""

from __future__ import annotations

from tkinter import DoubleVar, IntVar, StringVar, Tk, filedialog, messagebox, ttk

from .audio import INSTRUMENTS


def choose_settings() -> dict[str, object] | None:
    root = Tk()
    root.title("Music Game - Cài đặt")
    root.geometry("510x700")
    root.resizable(False, False)
    root.configure(bg="#18192b")
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("TFrame", background="#18192b")
    style.configure("TLabel", background="#18192b", foreground="#f1f1f7", font=("Segoe UI", 10))
    style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground="#78e4b1")
    style.configure("TButton", font=("Segoe UI", 10), padding=7)
    frame = ttk.Frame(root, padding=22)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="MUSIC GAME", style="Title.TLabel").pack(anchor="w")
    ttk.Label(frame, text="Chọn thiết bị và cách chơi trước khi bắt đầu.").pack(anchor="w", pady=(3, 18))

    source_kind = StringVar(value="Camera")
    camera = StringVar(value="0")
    video = StringVar(value="")
    mode = StringVar(value="free")
    instrument = StringVar(value="Piano")
    hand = StringVar(value="Right")
    volume = DoubleVar(value=55)
    buffer = StringVar(value="512")
    sensitivity = StringVar(value="Vừa")
    song = StringVar(value="Twinkle")
    chosen: dict[str, object] | None = None

    def row(label: str, widget) -> None:
        ttk.Label(frame, text=label).pack(anchor="w", pady=(7, 2))
        widget.pack(fill="x")

    row("Nguồn hình", ttk.Combobox(frame, textvariable=source_kind,
                                   values=("Camera", "Video"), state="readonly"))
    row("Camera (thử 0, 1, 2 hoặc 3)", ttk.Combobox(frame, textvariable=camera,
                                                   values=("0", "1", "2", "3"), state="readonly"))
    video_row = ttk.Frame(frame)
    ttk.Entry(video_row, textvariable=video).pack(side="left", fill="x", expand=True)
    ttk.Button(video_row, text="Chọn video", command=lambda: video.set(
        filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv"),
                                             ("Tất cả", "*.*")]) or video.get()
    )).pack(side="right", padx=(6, 0))
    row("Tệp video (chỉ dùng khi chọn Video)", video_row)
    row("Chế độ", ttk.Combobox(frame, textvariable=mode,
                              values=("free", "challenge", "melody"), state="readonly"))
    row("Bài nhạc cho chế độ melody", ttk.Combobox(frame, textvariable=song,
                                                   values=("Twinkle", "Scale"), state="readonly"))
    row("Nhạc cụ", ttk.Combobox(frame, textvariable=instrument,
                               values=INSTRUMENTS, state="readonly"))
    row("Tay chơi nốt", ttk.Combobox(frame, textvariable=hand,
                                    values=("Right", "Left"), state="readonly"))
    row("Độ nhạy nhận dạng", ttk.Combobox(frame, textvariable=sensitivity,
                                         values=("Nhanh", "Vừa", "Ổn định"), state="readonly"))
    row("Bộ đệm âm thanh (256 nhanh; 1024 ổn định)",
        ttk.Combobox(frame, textvariable=buffer, values=("256", "512", "1024"), state="readonly"))
    row("Âm lượng", ttk.Scale(frame, from_=0, to=100, variable=volume))

    def begin() -> None:
        nonlocal chosen
        if source_kind.get() == "Video" and not video.get().strip():
            messagebox.showerror("Thiếu video", "Hãy chọn một tệp video.", parent=root)
            return
        chosen = {
            "source": camera.get() if source_kind.get() == "Camera" else video.get(),
            "mode": mode.get(), "instrument": instrument.get(), "note_hand": hand.get(),
            "volume": volume.get() / 100.0, "buffer": int(buffer.get()),
            "sensitivity": sensitivity.get(), "song": song.get(),
        }
        root.destroy()

    ttk.Button(frame, text="BẮT ĐẦU CHƠI", command=begin).pack(fill="x", pady=(19, 0))
    root.mainloop()
    return chosen

