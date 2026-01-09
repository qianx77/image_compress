# gui_image_compressor.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import os
from PIL import Image, ImageTk, ImageCms
import piexif
import datetime
import requests  # 添加requests库导入
# 包含icc_profile和exif的完整压缩功能
# 加上exif的时间、地点、创作者的修改
# api key需要自己申请输入
# 添加作者信息
class ImageCompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("图片压缩工具")
        self.root.geometry("800x750")  # 增加高度以容纳新的EXIF编辑区域
        self.root.resizable(True, True)
        
        # 变量
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.quality_var = tk.IntVar(value=90)
        self.width_var = tk.IntVar(value=800)
        self.height_var = tk.IntVar(value=600)
        self.ratio_var = tk.DoubleVar(value=0.8)
        self.original_image = None
        self.compressed_image = None
        self.mode = tk.StringVar(value="quality")  # quality, size, ratio
        
        # EXIF编辑变量
        self.artist_var = tk.StringVar()
        self.datetime_var = tk.StringVar()
        self.gps_var = tk.StringVar()
        
        # EXIF修改控制变量（复选框）
        self.modify_artist_var = tk.BooleanVar(value=True)  # 默认修改创作者
        self.modify_datetime_var = tk.BooleanVar(value=True)  # 默认修改拍摄时间
        self.modify_gps_var = tk.BooleanVar(value=True)  # 默认修改GPS位置
        
        # 高德地图API密钥（可以替换为您自己的密钥）
        self.amap_key = tk.StringVar()
        
        self.setup_ui()
        self.setup_drag_and_drop()  # 初始化拖拽功能
        self.setup_clipboard()      # 初始化剪贴板功能
    def show_about(self):
        """显示关于对话框"""
        about_info = """
图片压缩工具 v1.0

功能：
- 图片压缩（质量、尺寸、比例三种模式），推荐直接按照质量压缩
- EXIF信息编辑（创作者、拍摄时间、GPS位置）
- 高德地图API地址转经纬度
- 拖拽文件支持
- 剪贴板支持


作者：Q

© [2026] 
        """
        messagebox.showinfo("关于图片压缩工具", about_info)
    def setup_ui(self):
        # 添加顶部按钮框架
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # 关于按钮（放在右上角）
        about_button = ttk.Button(top_frame, text="关于", command=self.show_about)
        about_button.pack(side=tk.RIGHT)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)  # 调整权重以适应新增的EXIF区域
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="输入文件:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(file_frame, textvariable=self.input_path, state="readonly").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(file_frame, text="浏览", command=self.browse_input).grid(row=0, column=2)
        
        ttk.Label(file_frame, text="输出文件:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Entry(file_frame, textvariable=self.output_path).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        ttk.Button(file_frame, text="浏览", command=self.browse_output).grid(row=1, column=2, pady=(5, 0))
        
        # 拖拽区域
        drag_frame = ttk.LabelFrame(main_frame, text="拖拽区域", padding="20")
        drag_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        drag_frame.columnconfigure(0, weight=1)
        
        self.drop_area = tk.Canvas(drag_frame, height=100, bg="#f0f0f0", relief="ridge", bd=2)
        self.drop_area.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.drop_area.create_text(200, 50, text="将图片拖拽到这里\n或点击选择文件", fill="#666666", font=("Arial", 12))
        
        # 参数设置区域
        param_frame = ttk.LabelFrame(main_frame, text="压缩参数", padding="10")
        param_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        param_frame.columnconfigure(0, weight=1)
        param_frame.rowconfigure(3, weight=1)
        
        # 压缩模式选择
        mode_frame = ttk.Frame(param_frame)
        mode_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(mode_frame, text="压缩模式:").pack(side=tk.LEFT)
        
        ttk.Radiobutton(mode_frame, text="按质量", variable=self.mode, value="quality", 
                       command=self.update_mode).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(mode_frame, text="按尺寸", variable=self.mode, value="size",
                       command=self.update_mode).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Radiobutton(mode_frame, text="按比例", variable=self.mode, value="ratio",
                       command=self.update_mode).pack(side=tk.LEFT, padx=(5, 0))
        
        # 各种参数控件
        self.quality_frame = ttk.Frame(param_frame)
        self.quality_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(self.quality_frame, text="质量 (0-100):").grid(row=0, column=0, sticky=tk.W)
        quality_scale = ttk.Scale(self.quality_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                 variable=self.quality_var, command=self.on_quality_change)
        quality_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 10))
        self.quality_label = ttk.Label(self.quality_frame, text=str(self.quality_var.get()))
        self.quality_label.grid(row=0, column=2, sticky=tk.W)
        self.quality_frame.columnconfigure(1, weight=1)
        
        self.size_frame = ttk.Frame(param_frame)
        self.size_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(self.size_frame, text="宽度:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(self.size_frame, textvariable=self.width_var, width=10).grid(row=0, column=1, padx=(5, 15))
        ttk.Label(self.size_frame, text="高度:").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(self.size_frame, textvariable=self.height_var, width=10).grid(row=0, column=3, padx=(5, 0))
        self.size_frame.grid_remove()  # 默认隐藏
        
        self.ratio_frame = ttk.Frame(param_frame)
        self.ratio_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(self.ratio_frame, text="比例 (0.1-1.0):").grid(row=0, column=0, sticky=tk.W)
        ratio_scale = ttk.Scale(self.ratio_frame, from_=0.1, to=1.0, orient=tk.HORIZONTAL,
                               variable=self.ratio_var, command=self.on_ratio_change)
        ratio_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 10))
        self.ratio_label = ttk.Label(self.ratio_frame, text=f"{self.ratio_var.get():.2f}")
        self.ratio_label.grid(row=0, column=2, sticky=tk.W)
        self.ratio_frame.columnconfigure(1, weight=1)
        self.ratio_frame.grid_remove()  # 默认隐藏
        
        # EXIF编辑区域
        exif_frame = ttk.LabelFrame(main_frame, text="EXIF信息编辑", padding="10")
        exif_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        exif_frame.columnconfigure(1, weight=1)

        # amap key输入
        ttk.Label(exif_frame, text="高德地图API Key:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=(0, 5))
        ttk.Entry(exif_frame, textvariable=self.amap_key).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(0, 5))
        
        # 创作者
        ttk.Label(exif_frame, text="创作者:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(0, 5))
        ttk.Entry(exif_frame, textvariable=self.artist_var).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(0, 5))
        ttk.Checkbutton(exif_frame, text="修改", variable=self.modify_artist_var).grid(row=1, column=2, padx=(0, 5), pady=(0, 5))
        
        # 拍摄时间
        ttk.Label(exif_frame, text="拍摄时间:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(0, 5))
        ttk.Entry(exif_frame, textvariable=self.datetime_var, width=30).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(0, 5))
        ttk.Button(exif_frame, text="使用当前时间", command=self.use_current_time).grid(row=2, column=2, padx=(0, 5), pady=(0, 5))
        # 设置默认时间为当前时间
        self.datetime_var.set(datetime.datetime.now().strftime("%Y:%m:%d %H:%M:%S"))
        
        # 添加拍摄时间的复选框（放在下一行）
        ttk.Checkbutton(exif_frame, text="修改拍摄时间", variable=self.modify_datetime_var).grid(row=3, column=1, sticky=tk.W, padx=(0, 5), pady=(0, 5))
        
        # GPS位置
        ttk.Label(exif_frame, text="GPS位置:").grid(row=4, column=0, sticky=tk.W, padx=(0, 5), pady=(0, 5))
        ttk.Entry(exif_frame, textvariable=self.gps_var).grid(row=4, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(0, 5))
        ttk.Checkbutton(exif_frame, text="修改", variable=self.modify_gps_var).grid(row=4, column=2, padx=(0, 5), pady=(0, 5))
        ttk.Label(exif_frame, text="(格式: 地址或 纬度,经度)", font=("Arial", 8)).grid(row=5, column=1, sticky=tk.W, padx=(0, 5))
        
        # 预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="预览", padding="10")
        preview_frame.grid(row=2, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="white")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 操作按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))
        button_frame.columnconfigure(1, weight=1)
        
        ttk.Button(button_frame, text="压缩", command=self.compress_image).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="重置", command=self.reset_all).pack(side=tk.RIGHT, padx=(0, 10))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def setup_drag_and_drop(self):
        """设置拖拽功能 - 使用更兼容的方法"""
        try:
            # 尝试使用tkinterdnd2
            import tkinterdnd2 as tkdnd
            self.drop_area.drop_target_register(tkdnd.DND_FILES)
            self.drop_area.dnd_bind('<<Drop>>', self.on_drop)
            # 添加视觉反馈
            self.drop_area.dnd_bind('<Enter>', self.on_drag_enter)
            self.drop_area.dnd_bind('<Leave>', self.on_drag_leave)
            self.drop_area.bind("<Button-1>", self.browse_input)
        except (ImportError, tk.TclError):
            # 如果tkinterdnd2不可用，使用基本的点击功能
            self.drop_area.bind("<Button-1>", self.browse_input)
            
    def setup_clipboard(self):
        """设置剪贴板功能"""
        # 绑定Ctrl+V快捷键
        self.root.bind('<Control-v>', self.paste_from_clipboard)
        self.root.bind('<Control-V>', self.paste_from_clipboard)
        
    def use_current_time(self):
        """使用当前时间填充拍摄时间文本框"""
        self.datetime_var.set(datetime.datetime.now().strftime("%Y:%m:%d %H:%M:%S"))
        
    def paste_from_clipboard(self, event=None):
        """从剪贴板粘贴图片"""
        try:
            # 尝试从剪贴板获取图片
            from PIL import ImageGrab
            clipboard_image = ImageGrab.grabclipboard()
            
            if clipboard_image is None:
                self.status_var.set("剪贴板中没有图片")
                return
                
            # 生成临时文件路径
            temp_dir = os.path.join(os.getcwd(), "temp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                
            temp_file = os.path.join(temp_dir, "clipboard_image.png")
            clipboard_image.save(temp_file)
            
            # 设置输入路径并加载图片
            self.input_path.set(temp_file)
            self.load_image(temp_file)
            self.status_var.set("已从剪贴板粘贴图片")
            
        except Exception as e:
            self.status_var.set(f"从剪贴板粘贴失败: {str(e)}")
    
    def browse_input(self, event=None):
        """浏览输入文件"""
        filename = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp")]
        )
        if filename:
            self.input_path.set(filename)
            self.load_image(filename)
            
            # 自动设置输出文件路径
            name, ext = os.path.splitext(filename)
            output_filename = name + "_compressed" + ext
            self.output_path.set(output_filename)
    
    def browse_output(self):
        """浏览输出文件"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG files", "*.jpg *.jpeg"), ("PNG files", "*.png"), 
                      ("BMP files", "*.bmp"), ("GIF files", "*.gif"), ("TIFF files", "*.tiff")]
        )
        if filename:
            self.output_path.set(filename)
    
    def update_mode(self):
        """更新压缩模式的显示"""
        mode = self.mode.get()
        
        # 隐藏所有参数框架
        self.quality_frame.grid_remove()
        self.size_frame.grid_remove()
        self.ratio_frame.grid_remove()
        
        # 显示当前模式的参数框架
        if mode == "quality":
            self.quality_frame.grid()
        elif mode == "size":
            self.size_frame.grid()
        elif mode == "ratio":
            self.ratio_frame.grid()
    
    def on_quality_change(self, event=None):
        """质量滑块变化时更新标签"""
        self.quality_label.config(text=str(self.quality_var.get()))
    
    def on_ratio_change(self, event=None):
        """比例滑块变化时更新标签"""
        self.ratio_label.config(text=f"{self.ratio_var.get():.2f}")
    
    def on_drop(self, event):
        """处理文件拖拽事件"""
        try:
            # 获取拖拽的文件路径
            files = self.drop_area.tk.splitlist(event.data)
            if files:
                filename = files[0]
                if os.path.isfile(filename):
                    self.input_path.set(filename)
                    self.load_image(filename)
                    
                    # 自动设置输出文件路径
                    name, ext = os.path.splitext(filename)
                    output_filename = name + "_compressed" + ext
                    self.output_path.set(output_filename)
                    self.status_var.set("已加载拖拽的文件")
                    
        except Exception as e:
            self.status_var.set(f"拖拽文件失败: {str(e)}")
    
    def on_drag_enter(self, event):
        """拖拽进入时改变背景色"""
        self.drop_area.config(bg="#e0e0ff")
    
    def on_drag_leave(self, event):
        """拖拽离开时恢复背景色"""
        self.drop_area.config(bg="#f0f0f0")
    
    def load_image(self, file_path):
        """加载图片并显示预览"""
        try:
            # 使用OpenCV读取图片
            img = cv2.imread(file_path)
            if img is None:
                messagebox.showerror("错误", "无法读取图片文件")
                return
                
            self.original_image = img
            
            # 转换颜色空间 (BGR to RGB)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 调整图片大小以适应预览区域
            h, w = img_rgb.shape[:2]
            canvas_w = 300
            canvas_h = 200
            scale = min(canvas_w/w, canvas_h/h, 1.0)
            new_w, new_h = int(w*scale), int(h*scale)
            
            # 调整图片大小
            img_resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # 转换为PIL Image然后转为PhotoImage
            pil_img = Image.fromarray(img_resized)
            self.photo = ImageTk.PhotoImage(pil_img)
            
            # 清除画布并显示图片
            self.preview_canvas.delete("all")
            x = (canvas_w - new_w) // 2
            y = (canvas_h - new_h) // 2
            self.preview_canvas.create_image(x, y, anchor=tk.NW, image=self.photo)
            self.preview_canvas.config(scrollregion=self.preview_canvas.bbox(tk.ALL))
            
            # 更新状态
            file_size = os.path.getsize(self.input_path.get())
            self.status_var.set(f"已加载图片: {w}x{h}, 大小: {file_size/(1024*1024):.2f}MB")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图片失败: {str(e)}")
    
    def get_gps_from_address(self, address: str, city: str = None):
        """
        使用高德地图地理编码 API 将地址转换为经纬度
        参数:
          address: 完整地址字符串
          city: 可选，具体城市名可以提高匹配精度
        返回:
          (lat, lon) 或 (None, None) 如果没有找到
        """
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": self.amap_key.get(),
            "address": address,
            "output": "JSON"
        }
        if city:
            params["city"] = city

        response = requests.get(url, params=params)
        data = response.json()

        # 判断返回是否成功并包含 geocodes
        if data.get("status") == "1" and data.get("geocodes"):
            # geocodes 是一个列表，取第一个匹配
            location = data["geocodes"][0].get("location")
            if location:
                lon, lat = location.split(",")
                return float(lat), float(lon)
        
        return None, None
    
    def deg_to_dms_rational(self, deg_float):
        """将度数转换为度分秒格式的有理数"""
        deg = int(deg_float)
        min_float = (deg_float - deg) * 60
        minute = int(min_float)
        sec_float = (min_float - minute) * 60
        return (
            (deg, 1),
            (minute, 1),
            (int(sec_float * 10000), 10000)
        )
    
    def string_to_bytes(self, input_string):
        """将字符串转换为字节"""
        return input_string.encode('utf-8')
        
    def compress_image(self):
        """压缩图片"""
        if not self.input_path.get():
            messagebox.showwarning("警告", "请先选择输入文件")
            return
            
        if not self.output_path.get():
            messagebox.showwarning("警告", "请指定输出文件路径")
            return
            
        try:
            self.status_var.set("正在压缩...")
            self.root.update()
            
            # 使用Pillow读取原始图片，保留EXIF信息
            original_image = Image.open(self.input_path.get())
            exif = original_image.info.get('exif')
            icc_profile = original_image.info.get('icc_profile')
            
            # 转换为RGB模式（如果是PNG可能有alpha通道）
            if original_image.mode in ('RGBA', 'LA'):
                original_image = original_image.convert('RGB')
            elif original_image.mode == 'CMYK':
                # 更准确的CMYK到RGB转换
                original_image = ImageCms.profileToProfile(original_image, 
                                                        ImageCms.createProfile("CMYK"),
                                                        ImageCms.createProfile("sRGB"))
            
            mode = self.mode.get()
            compressed_image = original_image.copy()
            
            if mode == "quality":
                # 按质量压缩
                quality = self.quality_var.get()
                ext = os.path.splitext(self.output_path.get())[1].lower()
                
            elif mode == "size":
                # 按尺寸压缩
                max_width = self.width_var.get()
                max_height = self.height_var.get()
                
                width, height = compressed_image.size
                scale_x = max_width / width
                scale_y = max_height / height
                scale = min(scale_x, scale_y, 1.0)
                
                if scale < 1.0:
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    compressed_image = compressed_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
            elif mode == "ratio":
                # 按比例压缩
                ratio = self.ratio_var.get()
                
                if ratio != 1.0:
                    width, height = compressed_image.size
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    
                    # 使用高质量的插值方法
                    compressed_image = compressed_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 应用EXIF修改
            if exif:
                exif_dict = piexif.load(exif)
            else:
                exif_dict = {
                    "0th": {},
                    "Exif": {},
                    "GPS": {},
                    "1st": {},
                    "thumbnail": None,
                }
            
            # 修复ComponentsConfiguration标签类型问题（标签41729）
            if 41729 in exif_dict['Exif']:
                value = exif_dict['Exif'][41729]
                if isinstance(value, int):
                    # 将整数转换为字节数组
                    exif_dict['Exif'][41729] = bytes([(value >> 24) & 0xff, 
                                                   (value >> 16) & 0xff, 
                                                   (value >> 8) & 0xff, 
                                                   value & 0xff])
            
            # 修改创作者（只有当复选框被选中时）
            if self.modify_artist_var.get() and self.artist_var.get():
                exif_dict["0th"][piexif.ImageIFD.Artist] = self.string_to_bytes(self.artist_var.get())
            
            # 修改拍摄时间（只有当复选框被选中时）
            if self.modify_datetime_var.get() and self.datetime_var.get():
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = self.string_to_bytes(self.datetime_var.get())
            
            # 修改GPS位置（只有当复选框被选中时）
            if self.modify_gps_var.get() and self.gps_var.get():
                gps_input = self.gps_var.get().strip()
                try:
                    # 尝试解析为经纬度
                    if ',' in gps_input:
                        lat, lon = map(float, gps_input.split(','))
                    else:
                        # 使用高德地图API将地址转换为经纬度
                        self.status_var.set("正在将地址转换为经纬度...")
                        self.root.update()
                        
                        # 尝试从地址中提取城市信息（简单处理）
                        city = None
                        if '市' in gps_input:
                            city = gps_input.split('市')[0] + '市'
                        
                        # 调用高德地图API
                        lat, lon = self.get_gps_from_address(gps_input, city=city)
                        
                        if lat is None or lon is None:
                            # messagebox.showwarning("警告", f"无法将地址 '{gps_input}' 转换为经纬度")
                            messagebox.showwarning("警告", f"请输入正确的高德api key，或检查地址 '{gps_input}' 是否有效")
                            lat, lon = None, None
                        else:
                            self.status_var.set(f"地址 '{gps_input}' 已转换为经纬度: {lat:.6f}, {lon:.6f}")
                    
                    if lat is not None and lon is not None:
                        # 设置GPS信息
                        exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = b"N" if lat >= 0 else b"S"
                        exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = self.deg_to_dms_rational(abs(lat))
                        
                        exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = b"E" if lon >= 0 else b"W"
                        exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = self.deg_to_dms_rational(abs(lon))
                except Exception as e:
                    messagebox.showwarning("警告", f"GPS处理错误: {str(e)}")
            
            # 转换为EXIF字节数据
            exif_bytes = piexif.dump(exif_dict)
            
            # 保存图片
            quality = self.quality_var.get() if mode == "quality" else 90
            if icc_profile:
                compressed_image.save(self.output_path.get(), quality=quality, optimize=True, exif=exif_bytes, icc_profile=icc_profile)
            else:
                compressed_image.save(self.output_path.get(), quality=quality, optimize=True, exif=exif_bytes)
            
            # 显示结果
            original_size = os.path.getsize(self.input_path.get())
            compressed_size = os.path.getsize(self.output_path.get())
            reduction = (1 - compressed_size / original_size) * 100
            
            messagebox.showinfo("完成", 
                            f"图片压缩完成!\n"
                            f"原图大小: {original_size/(1024*1024):.2f} MB\n"
                            f"压缩后大小: {compressed_size/(1024*1024):.2f} MB\n"
                            f"节省空间: {reduction:.1f}%")
            
            self.status_var.set("压缩完成")
            
        except Exception as e:
            messagebox.showerror("错误", f"压缩失败: {str(e)}")
            self.status_var.set("压缩失败")
            
    def reset_all(self):
        """重置所有设置"""
        self.input_path.set("")
        self.output_path.set("")
        self.quality_var.set(90)
        self.width_var.set(800)
        self.height_var.set(600)
        self.ratio_var.set(0.8)
        self.mode.set("quality")
        self.update_mode()
        self.preview_canvas.delete("all")
        self.status_var.set("就绪")
        
        # 重置EXIF编辑区域
        self.artist_var.set("")
        self.datetime_var.set(datetime.datetime.now().strftime("%Y:%m:%d %H:%M:%S"))
        self.gps_var.set("")
        # self.amap_key.set("")
        
        # 重置EXIF修改控制复选框
        self.modify_artist_var.set(True)
        self.modify_datetime_var.set(True)
        self.modify_gps_var.set(True)

def main():
    # 尝试使用tkinterdnd2创建根窗口以支持拖拽
    try:
        import tkinterdnd2 as tkdnd
        root = tkdnd.Tk()
    except ImportError:
        root = tk.Tk()
    except tk.TclError:
        # 如果tkinterdnd2初始化失败，回退到标准tk
        root = tk.Tk()

    # 设置窗口图标
    try:
        # 使用项目目录中的icon.ico文件
        #root.iconbitmap("icon.ico")
         # 使用PIL加载图标
        img = Image.open("icon.ico")
        photo = ImageTk.PhotoImage(img)
        root.iconphoto(True, photo)
    except Exception as e:
        # 如果图标设置失败，打印错误但不影响程序运行
        print(f"设置图标失败: {e}")
        
    app = ImageCompressorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    # 添加datetime导入（已经在文件顶部导入）
    try:
        from PIL import ImageGrab
    except ImportError:
        print("提示: 安装Pillow库以启用剪贴板功能: pip install Pillow")
        ImageGrab = None
    main()