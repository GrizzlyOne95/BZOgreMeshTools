import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import json
from pathlib import Path

# Platform check
IS_WINDOWS = sys.platform == "win32"
CONFIG_FILE = "ogre_tools_config.json"

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller bundling """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Ensure current dir is in sys.path for imports
current_dir = get_resource_path(".")
if current_dir not in sys.path:
    sys.path.append(current_dir)

class OgreMeshToolsGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OGRE MESH TOOLS")
        self.geometry("900x700")
        
        # --- THEME & COLORS ---
        self.colors = {
            "bg": "#0a0a0a",
            "fg": "#d4d4d4",
            "highlight": "#00ff00", # Neon Green
            "warning": "#ffff44",   # Amber/Gold
            "accent": "#00ffff",    # Cyan
            "dark": "#1a1a1a"
        }
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green") # matches highlight
        
        self.configure(fg_color=self.colors["bg"])
        
        self.resource_dir = get_resource_path(".")
        self.load_custom_fonts()
        
        # --- VARIABLES ---
        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.do_gltf = ctk.BooleanVar(value=True)
        self.do_obj = ctk.BooleanVar(value=False)
        self.do_normals = ctk.BooleanVar(value=False)
        self.batch_mode = ctk.BooleanVar(value=False)
        self.blender_path = ctk.StringVar()
        self.last_output_dir = ""
        
        self.load_config()
        self.setup_ui()
        
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
                    self.blender_path.set(cfg.get("blender_path", "blender"))
            except: pass
        else:
            self.blender_path.set("blender")

    def save_config(self):
        cfg = {"blender_path": self.blender_path.get()}
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(cfg, f, indent=4)
        except: pass
        
    def load_custom_fonts(self):
        self.main_font = "Consolas"
        if IS_WINDOWS:
            font_path = get_resource_path("BZONE.ttf")
            if os.path.exists(font_path):
                # AddFontResourceExW flag 0x10 is FR_PRIVATE (not enumerable by others)
                import ctypes
                ctypes.windll.gdi32.AddFontResourceExW(font_path, 0x10, 0)
                self.main_font = "BZONE"
                print(f"Loaded custom font: {self.main_font}")

    def setup_ui(self):
        # Header
        self.header = ctk.CTkLabel(self, text="OGRE MESH TOOLS", 
                                  font=(self.main_font, 32, "bold"), 
                                  text_color=self.colors["highlight"])
        self.header.pack(pady=(20, 10))
        
        self.subtitle = ctk.CTkLabel(self, text="BATTLEZONE CONVERSION UTILITY", 
                                    font=(self.main_font, 14), 
                                    text_color=self.colors["accent"])
        self.subtitle.pack(pady=(0, 20))

        # Main Frame
        self.main_container = ctk.CTkFrame(self, fg_color=self.colors["bg"])
        self.main_container.pack(fill="both", expand=True, padx=40, pady=10)

        # --- INPUT SECTION ---
        self.input_frame = ctk.CTkFrame(self.main_container, fg_color=self.colors["dark"])
        self.input_frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(self.input_frame, text="INPUT SOURCE", font=(self.main_font, 12, "bold"), text_color=self.colors["highlight"]).pack(anchor="w", padx=10, pady=(5,0))
        
        self.path_row = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.path_row.pack(fill="x", padx=10, pady=10)
        
        self.input_entry = ctk.CTkEntry(self.path_row, textvariable=self.input_path, placeholder_text="Select a .mesh file or directory...", fg_color="#050505", border_color=self.colors["highlight"])
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.browse_btn = ctk.CTkButton(self.path_row, text="BROWSE", command=self.browse_input, font=(self.main_font, 12), fg_color=self.colors["dark"], border_width=1, border_color=self.colors["highlight"], hover_color="#222")
        self.browse_btn.pack(side="right")
        
        self.mode_switch = ctk.CTkSwitch(self.input_frame, text="BATCH DIRECTORY MODE", variable=self.batch_mode, font=(self.main_font, 11), progress_color=self.colors["highlight"])
        self.mode_switch.pack(anchor="w", padx=10, pady=(0, 10))

        # --- CONFIG SECTION ---
        self.cfg_frame = ctk.CTkFrame(self.main_container, fg_color=self.colors["dark"])
        self.cfg_frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(self.cfg_frame, text="SETTINGS", font=(self.main_font, 12, "bold"), text_color=self.colors["highlight"]).pack(anchor="w", padx=10, pady=(5,0))
        
        self.blender_row = ctk.CTkFrame(self.cfg_frame, fg_color="transparent")
        self.blender_row.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkLabel(self.blender_row, text="Blender Path:", font=(self.main_font, 11)).pack(side="left", padx=(0, 10))
        self.blender_entry = ctk.CTkEntry(self.blender_row, textvariable=self.blender_path, fg_color="#050505", border_color=self.colors["highlight"], height=24)
        self.blender_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.blender_browse = ctk.CTkButton(self.blender_row, text="...", width=30, height=24, command=self.browse_blender)
        self.blender_browse.pack(side="right")

        # --- PROGRESS SECTION ---
        self.progress_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(10, 0), padx=5)
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="READY", font=(self.main_font, 10), text_color=self.colors["fg"])
        self.progress_label.pack(side="left")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, progress_color=self.colors["highlight"], fg_color=self.colors["dark"])
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(10, 0))
        self.progress_bar.set(0)

        # --- OPERATIONS ---
        self.ops_frame = ctk.CTkFrame(self.main_container, fg_color=self.colors["dark"])
        self.ops_frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(self.ops_frame, text="OPERATIONS", font=(self.main_font, 12, "bold"), text_color=self.colors["highlight"]).pack(anchor="w", padx=10, pady=(5,5))
        
        # glTF Row
        self.gltf_row = ctk.CTkFrame(self.ops_frame, fg_color="transparent")
        self.gltf_row.pack(fill="x", padx=20, pady=2)
        self.check_gltf = ctk.CTkCheckBox(self.gltf_row, text="CONVERT TO glTF (.glb)", variable=self.do_gltf, font=(self.main_font, 12), border_color=self.colors["highlight"], checkmark_color=self.colors["bg"])
        self.check_gltf.pack(side="left")
        ctk.CTkLabel(self.gltf_row, text="[ANIMATED / RIGGED - REQUIRES BLENDER]", font=(self.main_font, 10), text_color=self.colors["accent"]).pack(side="left", padx=10)
        
        # OBJ Row
        self.obj_row = ctk.CTkFrame(self.ops_frame, fg_color="transparent")
        self.obj_row.pack(fill="x", padx=20, pady=5)
        self.check_obj = ctk.CTkCheckBox(self.obj_row, text="CONVERT TO OBJ", variable=self.do_obj, font=(self.main_font, 12), border_color=self.colors["highlight"], checkmark_color=self.colors["bg"])
        self.check_obj.pack(side="left")
        ctk.CTkLabel(self.obj_row, text="[STATIC MESH - STANDALONE]", font=(self.main_font, 10), text_color=self.colors["fg"]).pack(side="left", padx=10)
        
        # Normals
        self.check_normals = ctk.CTkCheckBox(self.ops_frame, text="RECALCULATE NORMALS (Requires XML)", variable=self.do_normals, font=(self.main_font, 12), border_color=self.colors["highlight"], checkmark_color=self.colors["bg"])
        self.check_normals.pack(anchor="w", padx=20, pady=5)

        # --- LOGGING ---
        self.log_label = ctk.CTkLabel(self.main_container, text="TERMINAL OUTPUT", font=(self.main_font, 12, "bold"), text_color=self.colors["highlight"])
        self.log_label.pack(anchor="w", padx=5, pady=(10, 0))
        
        self.log_box = ctk.CTkTextbox(self.main_container, fg_color="#050505", text_color=self.colors["fg"], font=("Consolas", 12), border_width=1, border_color=self.colors["highlight"])
        self.log_box.pack(fill="both", expand=True, padx=5, pady=(5, 10))

        # --- ACTION BUTTON ---
        self.run_btn = ctk.CTkButton(self, text="INITIALIZE CONVERSION SEQUENCE", 
                                    command=self.start_process, 
                                    font=(self.main_font, 16, "bold"), 
                                    height=50, 
                                    fg_color=self.colors["dark"], 
                                    border_width=2, 
                                    border_color=self.colors["highlight"],
                                    hover_color=self.colors["highlight"],
                                    text_color=self.colors["highlight"])
        
        # Workaround for hover text color if needed, but let's stick to standard for now
        self.run_btn.configure(hover_color="#006600")
        self.run_btn.pack(fill="x", padx=45, pady=(10, 5))
        
        self.open_folder_btn = ctk.CTkButton(self, text="OPEN EXPORT DIRECTORY", 
                                            command=self.open_output_folder,
                                            font=(self.main_font, 12),
                                            fg_color="transparent",
                                            text_color=self.colors["accent"],
                                            hover_color=self.colors["dark"])
        self.open_folder_btn.pack(pady=(0, 20))

    def browse_blender(self):
        f = filedialog.askopenfilename(filetypes=[("Executable", "*.exe"), ("All Files", "*.*")])
        if f: 
            self.blender_path.set(f)
            self.save_config()

    def browse_input(self):
        if self.batch_mode.get():
            d = filedialog.askdirectory()
            if d: self.input_path.set(d)
        else:
            f = filedialog.askopenfilename(filetypes=[("Ogre Mesh", "*.mesh"), ("Ogre XML", "*.xml"), ("All Files", "*.*")])
            if f: self.input_path.set(f)

    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            if IS_WINDOWS:
                os.startfile(self.last_output_dir)
            else:
                subprocess.run(["xdg-open", self.last_output_dir])
        else:
            messagebox.showinfo("Note", "No export directory has been created yet.")

    def log(self, message, color=None):
        self.log_box.insert("end", f"> {message}\n")
        self.log_box.see("end")

    def start_process(self):
        path = self.input_path.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Input path does not exist.")
            return
        
        self.run_btn.configure(state="disabled", text="PROCESSING...")
        self.log_box.delete("1.0", "end")
        self.progress_bar.set(0)
        self.log("Starting operation sequence...")
        
        thread = threading.Thread(target=self.run_operations, daemon=True)
        thread.start()

    def run_operations(self):
        try:
            input_p = os.path.abspath(self.input_path.get())
            xml_converter = get_resource_path("OgreXMLConverter.exe")
            is_batch = self.batch_mode.get()
            
            # --- FILE LIST COLLECTION ---
            files_to_process = []
            if is_batch:
                for root, _, files in os.walk(input_p):
                    for f in files:
                        if f.lower().endswith(('.mesh', '.xml')):
                            files_to_process.append(os.path.join(root, f))
            else:
                files_to_process = [input_p]

            # --- 1. NORMAL RECALCULATION ---
            if self.do_normals.get():
                self.log(f"--- STARTING NORMAL RECALCULATION ({len(files_to_process)} files) ---")
                self.after(0, lambda: self.progress_label.configure(text="RECALCULATING NORMALS..."))
                import recalculate_normals
                
                corrected_count = 0
                for i, f_path in enumerate(files_to_process):
                    progress = (i / len(files_to_process)) * 0.33 if self.do_obj.get() or self.do_gltf.get() else (i / len(files_to_process))
                    self.after(0, lambda p=progress: self.progress_bar.set(p))
                    
                    f_name = os.path.basename(f_path)
                    target_xml = f_path
                    is_binary = f_path.lower().endswith(".mesh")
                    
                    if is_binary:
                        subprocess.run([f'"{xml_converter}"', f'"{f_path}"'], check=True, capture_output=True, shell=True)
                        target_xml = f_path + ".xml"
                        if not os.path.exists(target_xml):
                            target_xml = os.path.splitext(f_path)[0] + ".xml"
                    
                    if os.path.exists(target_xml):
                        status = recalculate_normals.recalculate_normals(target_xml)
                        if status == "CHANGED":
                            self.log(f"UPDATED: Corrected normals for {f_name}")
                            corrected_count += 1
                        else:
                            self.log(f"CHECKED: Normals already correct for {f_name}")
                        
                        if is_binary:
                            if status == "CHANGED":
                                self.log(f"Exporting updated {f_name} back to binary mesh...")
                                subprocess.run([f'"{xml_converter}"', f'"{target_xml}"'], check=True, capture_output=True, shell=True)
                            
                            # Cleanup temp XML
                            try: os.remove(target_xml)
                            except: pass
                    else:
                        self.log(f"WARNING: Could not find XML for {f_name}", self.colors["warning"])
                
                self.log(f"--- NORMAL RECALCULATION COMPLETE: {corrected_count}/{len(files_to_process)} corrected ---")

            # --- 2. OBJ CONVERSION ---
            if self.do_obj.get():
                self.after(0, lambda: self.progress_label.configure(text="CONVERTING TO OBJ..."))
                self.after(0, lambda: self.progress_bar.set(0.5 if self.do_gltf.get() else 0.8))
                self.log(f"--- STARTING OBJ CONVERSION ---")
                obj_script = get_resource_path("MeshToObj.py")
                output_dir = os.path.join(input_p if is_batch else os.path.dirname(input_p), "OBJ_Export")
                os.makedirs(output_dir, exist_ok=True)
                self.last_output_dir = output_dir
                
                cmd = [sys.executable, f'"{obj_script}"', f'"{input_p}"', "-o", f'"{output_dir}"']
                if is_batch:
                    cmd.append("--batch")
                
                result = subprocess.run(' '.join(cmd), capture_output=True, text=True, shell=True)
                self.log(result.stdout)
                
            # --- 3. glTF CONVERSION ---
            if self.do_gltf.get():
                self.after(0, lambda: self.progress_label.configure(text="CONVERTING TO glTF (BLENDER)..."))
                self.after(0, lambda: self.progress_bar.set(0.9))
                self.log(f"--- STARTING glTF CONVERSION (Blender) ---")
                gltf_script = get_resource_path("batch_ogre_to_gltf.py")
                output_dir = os.path.join(input_p if is_batch else os.path.dirname(input_p), "glTF_Export")
                os.makedirs(output_dir, exist_ok=True)
                self.last_output_dir = output_dir
                
                blender_cmd = self.blender_path.get()
                in_dir = input_p if is_batch else os.path.dirname(input_p)
                
                cmd = [f'"{blender_cmd}"', "-b", "-P", f'"{gltf_script}"', "--", f'"{in_dir}"', f'"{output_dir}"', f'"{xml_converter}"']
                result = subprocess.run(' '.join(cmd), capture_output=True, text=True, shell=True)
                self.log(result.stdout)
                
            self.after(0, lambda: self.progress_bar.set(1.0))
            self.after(0, lambda: self.progress_label.configure(text="COMPLETE"))
            self.log("OPERATION SEQUENCE COMPLETE.", self.colors["highlight"])
                
            self.log("OPERATION SEQUENCE COMPLETE.", self.colors["highlight"])
            messagebox.showinfo("Success", "All operations completed successfully.")
            
        except subprocess.CalledProcessError as e:
            self.log(f"PROCESS ERROR: {e.stderr.decode() if e.stderr else str(e)}")
            messagebox.showerror("Error", f"Subprocess failed: {e}")
        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            self.after(0, lambda: self.run_btn.configure(state="normal", text="INITIALIZE CONVERSION SEQUENCE"))

if __name__ == "__main__":
    app = OgreMeshToolsGUI()
    app.mainloop()
