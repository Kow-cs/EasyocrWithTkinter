import tkinter as tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter import scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import cv2
import easyocr


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()
        self.geometry(f'{width}x{height}+0+0')
        self.title("OCR text editor")
        self.ocr_tool = OcrTool()
        self.file_manager = FileManager()

        self.canvas_frame = CanvasFrame(self)
        self.canvas_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.text_editor = TextEditor(self)
        self.text_editor.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.buttons = Buttons(self)
        self.buttons.pack()
        self.canvas_frame.text_editor = self.text_editor

class CanvasFrame(tk.LabelFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.files = master.file_manager
        self.text_editor = None
        self.box_area = dict()
        self.canvas = tk.Canvas(self)
        self.ocr_tool = master.ocr_tool
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind('<<Drop>>', self.drop_handler)
        self.canvas.bind("<Button-1>", self.on_left_click)


        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.image_draw()

    
    def drop_handler(self, event):
        print("dropped")
        file_paths = event.data.split()
        print(file_paths)
        for file_path in file_paths:
            self.files.set_input(file_path)
        self.image_draw()


    def image_draw(self):
        self.pil_image = Image.open(self.files.open_input_file())

        self.canvas_width = self.pil_image.width
        self.canvas_height = self.pil_image.height

        center_x = self.canvas_width / 2
        center_y = self.canvas_height / 2

        self.canvas.delete("current_image")

        self.photo_image = ImageTk.PhotoImage(self.pil_image)
        self.canvas.create_image(
            center_x,
            center_y,
            anchor="center",
            image=self.photo_image,
            tag="current_image"
        )
        
        self.generate_ocr_box()

    def generate_ocr_box(self):
        img_path = self.files.open_input_file()
        self.box_area.clear()
        if img_path != "default.png":
            self.ocr_tool.ocr_img(img_path)
            results =  self.ocr_tool.results
            for result in results:
                bbox, text, prob = result
                pt1 = (int(bbox[0][0]), int(bbox[0][1]))
                pt2 = (int(bbox[2][0]), int(bbox[2][1]))
                self.canvas.create_rectangle(
                    pt1[0], pt1[1], pt2[0], pt2[1], 
                    outline="green", 
                    tag="current_image"
                )
                key = f"{pt1[0]} {pt2[0]} {pt1[1]} {pt2[1]}"
                self.box_area.setdefault(key, text)
    
    def on_left_click(self, event):
        boxes = [list(map(int, key.split())) for key in self.box_area.keys()]
        x = event.x
        y = event.y
        for i, box in enumerate(boxes):
            if box[0] <= x and x <= box[1]:
                if box[2] <= y and y <= box[3]:
                    text = self.box_area[list(self.box_area.keys())[i]]
                    self.text_editor.text.insert(tk.END, text)

class TextEditor(tk.LabelFrame):
    def __init__(self, master):
        super().__init__(master)
        self.files = master.file_manager
        self.ocr_tool = master.ocr_tool
        self.text = scrolledtext.ScrolledText(self)
        self.text.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    def save_text(self):
        file = asksaveasfilename(
            title="txtファイルを開く",
            filetypes=[("テキストファイル", ".txt .md")],
            initialfile=self.files.open_input_file()[:-4] + ".txt"
        )
        if not file:
            file = self.files.open_input_file()[:-4] + ".txt"
        with open(file, "w") as save_file:
            text = self.text.get("1.0", tk.END)
            save_file.write(text)

    def display_ocr_results(self, results):
        # self.text.delete("1.0", tk.END)
        for bbox, text, prob in results:
            self.text.insert(tk.END, f"{text}\n")

    def clear_text(self):
        self.text.delete("1.0", tk.END)

class FileManager:
    def __init__(self):
        self.input_files = []
        self.counter = 0
        self.extensions = [".png", ".jpg", ".gif", ".pdf"]
        self.output_file = "result.txt"

    def set_input(self, file):
        if file[-4:] in self.extensions:
            self.input_files.append(file)

    def open_input_file(self):
        self.counter = len(self.input_files) - 1
        if self.counter >= 0:
            return self.input_files[self.counter]
        else:
            return "default.png"

class Buttons(tk.LabelFrame):
    def __init__(self, master):
        super().__init__(master)
        self.canvas = master.canvas_frame
        self.editor = master.text_editor
        self.files = master.file_manager

        self.open_button = tk.Button(self, text="Open", command=self.open_image)
        self.open_button.pack()
        self.save_button = tk.Button(self, text="Save", command=self.editor.save_text)
        self.save_button.pack()
        self.ocr_button = tk.Button(self, text="OCR", command=self.ocr_text)
        self.ocr_button.pack()
        self.clear_button = tk.Button(self, text="Clear", command = self.clear_text)
        self.clear_button.pack()

    def open_image(self):
        file = askopenfilename(
            title="画像ファイルを開く",
            multiple=False,
            filetypes=[("画像ファイル", ".png .jpg .jpeg .gif")]
        )
        self.files.set_input(file)

        self.canvas.image_draw()
        self.editor.clear_text()

    def ocr_text(self):
        img_path = self.files.open_input_file()
        if img_path != "default.png":
            results = self.canvas.ocr_tool.results
            self.editor.display_ocr_results(results)

    def clear_text(self):
        self.editor.clear_text()

class OcrTool:
    def __init__(self, langs=['ja', 'en'], gpu_op=True):
        self.reader = easyocr.Reader(langs, gpu=gpu_op)
        self.reset()

    def ocr_img(self, img_path):
        img = cv2.imread(img_path)
        self.filename = img_path
        self.results = self.reader.readtext(img)

    def reset(self):
        self.filename = None
        self.results = None


if __name__ == "__main__":
    app = App()
    app.mainloop()
