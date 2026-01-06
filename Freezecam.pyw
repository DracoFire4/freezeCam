import cv2
import pyvirtualcam
import tkinter as tk
from tkinter import ttk, messagebox
from pygrabber.dshow_graph import FilterGraph
from PIL import Image, ImageTk
import ctypes

# ==========================
# CONFIG
# ==========================
WINDOW_W = 640
WINDOW_H = 480

PREVIEW_W = 560
PREVIEW_H = 315

BG = "#1e1e1e"
FG = "#ffffff"
BTN = "#333333"

# ==========================
# Camera setup
# ==========================
def list_camera_names():
    graph = FilterGraph()
    return graph.get_input_devices()

camera_names = list_camera_names()
if not camera_names:
    messagebox.showerror("Error", "No cameras detected!")
    exit()

cap = None
cam = None
freeze_frame = None
freeze = False

# ==========================
# Main window
# ==========================
root = tk.Tk()
root.title("FreezeCam")
root.geometry(f"{WINDOW_W}x{WINDOW_H}")
root.resizable(False, False)
root.configure(bg=BG)


GWL_STYLE = -16
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000

hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
style &= ~WS_MINIMIZEBOX
style &= ~WS_MAXIMIZEBOX
ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

# ==========================
# UI Layout
# ==========================
frame = tk.Frame(root, bg=BG)
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

tk.Label(frame, text="Select Real Camera", bg=BG, fg=FG).pack(pady=(0, 5))

real_cam_combo = ttk.Combobox(frame, values=camera_names, state="readonly")
real_cam_combo.current(0)
real_cam_combo.pack(pady=(0, 8))

status_label = tk.Label(frame, text="Status: Not started", bg=BG, fg=FG)
status_label.pack(pady=(0, 8))


preview_container = tk.Frame(frame, bg="black", width=PREVIEW_W, height=PREVIEW_H)
preview_container.pack(pady=(0, 10))
preview_container.pack_propagate(False)

preview_label = tk.Label(preview_container, bg="black")
preview_label.place(relx=0.5, rely=0.5, anchor="center")

# ==========================
# Controls
# ==========================
def toggle_freeze():
    global freeze
    freeze = not freeze
    status_label.config(text="Status: Frozen" if freeze else "Status: Live")

def start_camera():
    global cap, cam
    cam_name = real_cam_combo.get()
    graph = FilterGraph()
    cam_index = graph.get_input_devices().index(cam_name)

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        messagebox.showerror("Error", "Failed to open camera")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if cam:
        cam.close()

    cam = pyvirtualcam.Camera(
        width=width,
        height=height,
        fps=30,
        device="OBS Virtual Camera"
    )

    status_label.config(text="Status: Live")
    start_btn.pack_forget()  

tk.Button(frame, text="Freeze / Unfreeze", bg=BTN, fg=FG, command=toggle_freeze).pack(side=tk.BOTTOM)

start_btn = tk.Button(frame, text="Start Camera", bg=BTN, fg=FG, command=start_camera)
start_btn.pack(pady=(0, 6), side=tk.BOTTOM)

# ==========================
# Aspect-ratio
# ==========================
def resize_with_letterbox(img, box_w, box_h):
    h, w, _ = img.shape
    scale = min(box_w / w, box_h / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)

    canvas = cv2.cvtColor(
        cv2.resize(
            cv2.cvtColor(img, cv2.COLOR_RGB2GRAY),
            (box_w, box_h)
        ),
        cv2.COLOR_GRAY2RGB
    )
    canvas[:] = 0  

    x = (box_w - nw) // 2
    y = (box_h - nh) // 2
    canvas[y:y+nh, x:x+nw] = resized
    return canvas

# ==========================
# Camera loop
# ==========================
def update_frame():
    global freeze_frame
    if cap and cam:
        ret, frame = cap.read()
        if ret:
            if freeze:
                if freeze_frame is None:
                    freeze_frame = frame.copy()
                frame = freeze_frame
            else:
                freeze_frame = None

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Send full-res frame
            cam.send(frame_rgb)
            cam.sleep_until_next_frame()

            # Letterboxed preview
            preview = resize_with_letterbox(frame_rgb, PREVIEW_W, PREVIEW_H)
            img = Image.fromarray(preview)
            imgtk = ImageTk.PhotoImage(img)

            preview_label.configure(image=imgtk)
            preview_label.image = imgtk

    root.after(10, update_frame)

# ==========================
# Cleanup
# ==========================
def on_close():
    if cap:
        cap.release()
    if cam:
        cam.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.after(10, update_frame)
root.mainloop()
