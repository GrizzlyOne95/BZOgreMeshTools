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
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

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

class ConsoleRedirector:
    def __init__(self, log_func):
        self.log_func = log_func
    def write(self, string):
        if string.strip():
            self.log_func(string.strip())
    def flush(self):
        pass

# ── COMMAND LINE MODE (FOR SUBPROCESSES) ──────────────────────────────────────
# If the EXE is launched with arguments, check if we need to run a tool instead
# of the GUI. This handles any legacy code using sys.executable subprocess calls.
if getattr(sys, 'frozen', False) and len(sys.argv) > 1:
    # Check for script-proxy mode
    arg1 = sys.argv[1].lower()
    if "meshtoobj" in arg1:
        import MeshToObj
        # Mock sys.argv for the target script
        sys.argv = sys.argv[1:]
        MeshToObj.main()
        sys.exit(0)
    elif "batch_ogre_to_gltf" in arg1:
        import batch_ogre_to_gltf
        sys.argv = sys.argv[1:]
        batch_ogre_to_gltf.main()
        sys.exit(0)

class OgreMeshToolsGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OGRE MESH TOOLS")
        self.geometry("1200x850")
        
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
        
        # Capture stdout/stderr AFTER UI is setup
        sys.stdout = ConsoleRedirector(self.log)
        sys.stderr = ConsoleRedirector(self.log)
        
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
        cfg = {
            "blender_path": self.blender_path.get()
        }
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

        # --- ACTION BUTTONS (Packed bottom-up to ensure visibility) ---
        self.open_folder_btn = ctk.CTkButton(self, text="OPEN EXPORT DIRECTORY", 
                                            command=self.open_output_folder,
                                            font=(self.main_font, 12),
                                            fg_color="transparent",
                                            text_color=self.colors["accent"],
                                            hover_color=self.colors["dark"])
        self.open_folder_btn.pack(side="bottom", pady=(0, 20))

        self.run_btn = ctk.CTkButton(self, text="PROCESS MESHES", 
                                    command=self.start_process, 
                                    font=(self.main_font, 16, "bold"), 
                                    height=50, 
                                    fg_color=self.colors["dark"], 
                                    border_width=2, 
                                    border_color=self.colors["highlight"],
                                    hover_color=self.colors["highlight"],
                                    text_color=self.colors["highlight"])
        self.run_btn.configure(hover_color="#006600")
        self.run_btn.pack(side="bottom", fill="x", padx=45, pady=(10, 5))

        # Main Frame setup for splits
        self.main_container = ctk.CTkFrame(self, fg_color=self.colors["bg"])
        self.main_container.pack(fill="both", expand=True, padx=40, pady=10)

        # Left Column (Settings and operations)
        self.left_col = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Right Column (Preview)
        self.right_col = ctk.CTkFrame(self.main_container, fg_color=self.colors["dark"])
        self.right_col.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(self.right_col, text="MESH PREVIEW", font=(self.main_font, 12, "bold"), text_color=self.colors["highlight"]).pack(anchor="w", padx=10, pady=(5,0))
        
        try:
            import ogre_preview
            self.preview_frame = ogre_preview.OgrePreviewFrame(self.right_col)
            self.preview_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        except ImportError:
            lbl = ctk.CTkLabel(self.right_col, text="Ogre preview not available.\nRun 'py -3.10 -m pip install ogre-python' first.")
            lbl.pack(expand=True)
            self.preview_frame = None

        # --- INPUT SECTION ---
        self.input_frame = ctk.CTkFrame(self.left_col, fg_color=self.colors["dark"])
        self.input_frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(self.input_frame, text="INPUT SOURCE", font=(self.main_font, 12, "bold"), text_color=self.colors["highlight"]).pack(anchor="w", padx=10, pady=(5,0))
        
        self.path_row = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.path_row.pack(fill="x", padx=10, pady=(10, 5))
        
        self.input_entry = ctk.CTkEntry(self.path_row, textvariable=self.input_path, placeholder_text="Select a .mesh file or directory...", fg_color="#050505", border_color=self.colors["highlight"])
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.preview_btn = ctk.CTkButton(self.path_row, text="PREVIEW", command=self.preview_mesh, font=(self.main_font, 12, "bold"), fg_color=self.colors["dark"], border_width=1, border_color=self.colors["accent"], hover_color="#222", text_color=self.colors["accent"])
        self.preview_btn.pack(side="right", padx=(10, 0))

        self.browse_btn = ctk.CTkButton(self.path_row, text="BROWSE", command=self.browse_input, font=(self.main_font, 12), fg_color=self.colors["dark"], border_width=1, border_color=self.colors["highlight"], hover_color="#222")
        self.browse_btn.pack(side="right")
        
        self.out_row = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.out_row.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkLabel(self.out_row, text="OUTPUT:", font=(self.main_font, 11), text_color=self.colors["fg"]).pack(side="left", padx=(0, 8))
        
        self.output_entry = ctk.CTkEntry(self.out_row, textvariable=self.output_path, placeholder_text="Output Destination (Optional)...", fg_color="#050505", border_color=self.colors["highlight"])
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.browse_out_btn = ctk.CTkButton(self.out_row, text="BROWSE", command=self.browse_output, font=(self.main_font, 12), fg_color=self.colors["dark"], border_width=1, border_color=self.colors["highlight"], hover_color="#222")
        self.browse_out_btn.pack(side="right")
        
        self.mode_switch = ctk.CTkSwitch(self.input_frame, text="BATCH DIRECTORY MODE", variable=self.batch_mode, font=(self.main_font, 11), progress_color=self.colors["highlight"])
        self.mode_switch.pack(anchor="w", padx=10, pady=(0, 10))

        # --- CONFIG SECTION ---
        self.cfg_frame = ctk.CTkFrame(self.left_col, fg_color=self.colors["dark"])
        self.cfg_frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(self.cfg_frame, text="SETTINGS", font=(self.main_font, 12, "bold"), text_color=self.colors["highlight"]).pack(anchor="w", padx=10, pady=(5,0))
        
        self.blender_row = ctk.CTkFrame(self.cfg_frame, fg_color="transparent")
        self.blender_row.pack(fill="x", padx=10, pady=(5, 5))
        
        ctk.CTkLabel(self.blender_row, text="Blender Path:", font=(self.main_font, 11)).pack(side="left", padx=(0, 10))
        self.blender_entry = ctk.CTkEntry(self.blender_row, textvariable=self.blender_path, fg_color="#050505", border_color=self.colors["highlight"], height=24)
        self.blender_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.blender_browse = ctk.CTkButton(self.blender_row, text="...", width=30, height=24, command=self.browse_blender)
        self.blender_browse.pack(side="right")

        # --- PROGRESS SECTION ---
        self.progress_frame = ctk.CTkFrame(self.left_col, fg_color="transparent")
        self.progress_frame.pack(fill="x", pady=(10, 0), padx=5)
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="READY", font=(self.main_font, 10), text_color=self.colors["fg"])
        self.progress_label.pack(side="left")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, progress_color=self.colors["highlight"], fg_color=self.colors["dark"])
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(10, 0))
        self.progress_bar.set(0)

        # --- OPERATIONS ---
        self.ops_frame = ctk.CTkFrame(self.left_col, fg_color=self.colors["dark"])
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
        self.log_label = ctk.CTkLabel(self.left_col, text="TERMINAL OUTPUT", font=(self.main_font, 12, "bold"), text_color=self.colors["highlight"])
        self.log_label.pack(anchor="w", padx=5, pady=(10, 0))
        
        self.log_box = ctk.CTkTextbox(self.left_col, fg_color="#050505", text_color=self.colors["fg"], font=("Consolas", 12), border_width=1, border_color=self.colors["highlight"])
        self.log_box.pack(fill="both", expand=True, padx=5, pady=(5, 10))

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

    def browse_output(self):
        d = filedialog.askdirectory()
        if d: self.output_path.set(d)

    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            if IS_WINDOWS:
                os.startfile(self.last_output_dir)
            else:
                subprocess.run(["xdg-open", self.last_output_dir], creationflags=CREATE_NO_WINDOW)
        else:
            messagebox.showinfo("Note", "No export directory has been created yet.")

    def preview_mesh(self):
        path = self.input_path.get()
        
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Please select a valid input mesh or directory to preview.")
            return
            
        if self.batch_mode.get():
            # In batch mode, try to find the first .mesh file to preview
            for root, _, files in os.walk(path):
                for f in files:
                    if f.lower().endswith('.mesh'):
                        path = os.path.join(root, f)
                        break
                if path.lower().endswith('.mesh'):
                    break
                    
            if not path.lower().endswith('.mesh'):
                messagebox.showerror("Error", "No .mesh files found in the selected batch directory to preview.")
                return
                
        if not path.lower().endswith('.mesh'):
            messagebox.showerror("Error", "Selected file is not a valid .mesh file.")
            return
            
        self.log(f"Loading native preview for: {os.path.basename(path)}")
        try:
            if self.preview_frame:
                self.preview_frame.load_mesh(path)
            else:
                self.log("Preview frame failed to initialize earlier.", self.colors["warning"])
        except Exception as e:
            self.log(f"Failed to load mesh in viewer: {str(e)}", self.colors["warning"])

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
                        subprocess.run([f'"{xml_converter}"', f'"{f_path}"'], check=True, capture_output=True, shell=True, creationflags=CREATE_NO_WINDOW)
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
                                subprocess.run([f'"{xml_converter}"', f'"{target_xml}"'], check=True, capture_output=True, shell=True, creationflags=CREATE_NO_WINDOW)
                            
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
                
                try:
                    import MeshToObj
                    req_out = self.output_path.get()
                    if req_out and os.path.exists(req_out):
                        output_dir = req_out
                    else:
                        output_dir = os.path.join(input_p if is_batch else os.path.dirname(input_p), "OBJ_Export")
                        os.makedirs(output_dir, exist_ok=True)
                    
                    self.last_output_dir = output_dir
                    
                    # Call MeshToObj logic directly in this thread
                    xml_conv = MeshToObj.OgreXMLConverter(os.path.dirname(xml_converter))
                    
                    if is_batch:
                        # Batch logic from MeshToObj.main
                        output_p = Path(output_dir)
                        xml_dir = output_p / 'xml_temp'
                        xml_dir.mkdir(exist_ok=True)
                        
                        self.log(f"Converting meshes to XML...")
                        xml_files = xml_conv.batch_convert(input_p, xml_dir)
                        
                        self.log(f"Converting XML to OBJ...")
                        for xml_f in xml_files:
                            xml_path = Path(xml_f)
                            obj_name = xml_path.name.replace('.mesh.xml', '.obj').replace('.xml', '.obj')
                            obj_file = output_p / obj_name
                            
                            converter = MeshToObj.OgreXMLToOBJ()
                            converter.convert(xml_f, obj_file, create_mtl=True)
                        
                        import shutil
                        shutil.rmtree(xml_dir)
                    else:
                        # Single file logic from MeshToObj.main
                        output_p = Path(output_dir)
                        obj_name = Path(input_p).name.replace('.mesh.xml', '.obj').replace('.mesh', '.obj').replace('.xml', '.obj')
                        if not obj_name.endswith('.obj'): obj_name += '.obj'
                        target_obj = output_p / obj_name
                        
                        xml_f = xml_conv.convert_to_xml(input_p)
                        if xml_f:
                            converter = MeshToObj.OgreXMLToOBJ()
                            converter.convert(xml_f, target_obj, create_mtl=True)
                            os.remove(xml_f)
                        else:
                            self.log("XML Conversion failed.", self.colors["warning"])
                    
                    self.log("OBJ Conversion completed.")
                except Exception as e:
                    self.log(f"OBJ ERROR: {str(e)}", self.colors["warning"])
                
            # --- 3. glTF CONVERSION ---
            if self.do_gltf.get():
                self.after(0, lambda: self.progress_label.configure(text="CONVERTING TO glTF (BLENDER)..."))
                self.after(0, lambda: self.progress_bar.set(0.9))
                self.log(f"--- STARTING glTF CONVERSION (Blender) ---")
                
                blender_cmd = self.blender_path.get()
                gltf_script = get_resource_path("batch_ogre_to_gltf.py")
                
                req_out = self.output_path.get()
                if req_out and os.path.exists(req_out):
                    output_dir = req_out
                else:
                    output_dir = os.path.join(input_p if is_batch else os.path.dirname(input_p), "glTF_Export")
                    os.makedirs(output_dir, exist_ok=True)
                
                self.last_output_dir = output_dir
                in_dir = input_p if is_batch else os.path.dirname(input_p)
                
                # Blender still needs a subprocess because it's its own executable. 
                # This call is SAFE because it calls blender.exe, NOT sys.executable.
                cmd = [f'"{blender_cmd}"', "-b", "-P", f'"{gltf_script}"', "--", f'"{in_dir}"', f'"{output_dir}"', f'"{xml_converter}"']
                result = subprocess.run(' '.join(cmd), capture_output=True, text=True, shell=True, creationflags=CREATE_NO_WINDOW)
                self.log(result.stdout)
                
            self.after(0, lambda: self.progress_bar.set(1.0))
            self.after(0, lambda: self.progress_label.configure(text="COMPLETE"))
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
            self.after(0, lambda: self.run_btn.configure(state="normal", text="PROCESS MESHES"))

if __name__ == "__main__":
    app = OgreMeshToolsGUI()
    app.mainloop()
