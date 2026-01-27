import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pygame
import os
import threading
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
import sys

# For getting audio duration
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC
from mutagen.wave import WAVE
from mutagen import File as MutagenFile

class AudioPlayer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎵 Audio Player")
        self.root.geometry("500x520")
        self.root.resizable(False, False)
        self.root.configure(bg='#1a1a2e')
        
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # State variables
        self.playlist = []  # List of file paths
        self.current_index = 0  # Current track index
        self.current_file = None
        self.current_duration = 0  # Duration in seconds
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.5
        self.tray_icon = None
        self.hidden = False
        
        # Create interface
        self.create_widgets()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        
        # Start update loops
        self.update_progress()
        self.check_music_end()
        
    def get_audio_duration(self, file_path):
        """Get duration of audio file in seconds"""
        try:
            # Try to detect file type and get duration
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.mp3':
                audio = MP3(file_path)
                return audio.info.length
            elif ext == '.ogg':
                audio = OggVorbis(file_path)
                return audio.info.length
            elif ext == '.flac':
                audio = FLAC(file_path)
                return audio.info.length
            elif ext == '.wav':
                audio = WAVE(file_path)
                return audio.info.length
            else:
                # Try generic mutagen
                audio = MutagenFile(file_path)
                if audio is not None and hasattr(audio.info, 'length'):
                    return audio.info.length
                return 0
        except Exception as e:
            print(f"Error getting duration: {e}")
            return 0
            
    def format_time(self, seconds):
        """Format seconds to MM:SS"""
        if seconds < 0:
            seconds = 0
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
        
    def create_widgets(self):
        # Title
        title_label = tk.Label(
            self.root, 
            text="🎵 Audio Player", 
            font=("Arial", 20, "bold"),
            fg='#e94560',
            bg='#1a1a2e'
        )
        title_label.pack(pady=10)
        
        # Frame for current file info
        info_frame = tk.Frame(self.root, bg='#16213e', relief='ridge', bd=2)
        info_frame.pack(fill='x', padx=20, pady=5)
        
        self.file_label = tk.Label(
            info_frame,
            text="No file selected",
            font=("Arial", 10),
            fg='#ffffff',
            bg='#16213e',
            wraplength=380
        )
        self.file_label.pack(pady=10, padx=10)
        
        # Playback status
        self.status_label = tk.Label(
            self.root,
            text="⏹ Stopped",
            font=("Arial", 12),
            fg='#0f3460',
            bg='#1a1a2e'
        )
        self.status_label.pack(pady=5)
        
        # Progress bar style
        style = ttk.Style()
        style.configure("Custom.Horizontal.TProgressbar", 
                       troughcolor='#16213e', 
                       background='#e94560')
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.root,
            style="Custom.Horizontal.TProgressbar",
            length=400,
            mode='determinate',
            maximum=100
        )
        self.progress_bar.pack(pady=5)
        
        # Time display - current / total
        self.time_label = tk.Label(
            self.root,
            text="00:00 / 00:00",
            font=("Arial", 10),
            fg='#ffffff',
            bg='#1a1a2e'
        )
        self.time_label.pack()
        
        # Track counter
        self.track_label = tk.Label(
            self.root,
            text="Track: 0 / 0",
            font=("Arial", 10),
            fg='#e94560',
            bg='#1a1a2e'
        )
        self.track_label.pack(pady=5)
        
        # Control buttons frame
        control_frame = tk.Frame(self.root, bg='#1a1a2e')
        control_frame.pack(pady=10)
        
        # Button style
        btn_style = {
            'font': ("Arial", 14),
            'width': 4,
            'height': 1,
            'bg': '#16213e',
            'fg': 'white',
            'activebackground': '#e94560',
            'activeforeground': 'white',
            'relief': 'flat',
            'cursor': 'hand2'
        }
        
        # Open file button
        self.btn_open = tk.Button(
            control_frame,
            text="📁",
            command=self.open_files,
            **btn_style
        )
        self.btn_open.grid(row=0, column=0, padx=5)
        
        # Previous track button
        self.btn_prev = tk.Button(
            control_frame,
            text="⏮",
            command=self.prev_track,
            **btn_style
        )
        self.btn_prev.grid(row=0, column=1, padx=5)
        
        # Rewind button
        self.btn_rewind = tk.Button(
            control_frame,
            text="⏪",
            command=self.rewind,
            **btn_style
        )
        self.btn_rewind.grid(row=0, column=2, padx=5)
        
        # Play/Pause button
        self.btn_play = tk.Button(
            control_frame,
            text="▶",
            command=self.play_pause,
            **btn_style
        )
        self.btn_play.grid(row=0, column=3, padx=5)
        
        # Forward button
        self.btn_forward = tk.Button(
            control_frame,
            text="⏩",
            command=self.forward,
            **btn_style
        )
        self.btn_forward.grid(row=0, column=4, padx=5)
        
        # Stop button
        self.btn_stop = tk.Button(
            control_frame,
            text="⏹",
            command=self.stop,
            **btn_style
        )
        self.btn_stop.grid(row=0, column=5, padx=5)
        
        # Next track button
        self.btn_next = tk.Button(
            control_frame,
            text="⏭",
            command=self.next_track,
            **btn_style
        )
        self.btn_next.grid(row=0, column=6, padx=5)
        
        # Volume frame
        volume_frame = tk.Frame(self.root, bg='#1a1a2e')
        volume_frame.pack(pady=10)
        
        # Volume icon
        self.volume_icon = tk.Label(
            volume_frame,
            text="🔊",
            font=("Arial", 14),
            fg='white',
            bg='#1a1a2e'
        )
        self.volume_icon.pack(side='left', padx=5)
        
        # Volume percentage label - CREATE BEFORE SLIDER!
        self.volume_label = tk.Label(
            volume_frame,
            text="50%",
            font=("Arial", 10),
            fg='white',
            bg='#1a1a2e',
            width=4
        )
        
        # Volume slider
        self.volume_slider = ttk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient='horizontal',
            length=250,
            command=self.change_volume
        )
        self.volume_slider.set(50)
        self.volume_slider.pack(side='left', padx=5)
        
        # Pack volume label after slider
        self.volume_label.pack(side='left', padx=5)
        
        # Playlist frame
        playlist_frame = tk.Frame(self.root, bg='#1a1a2e')
        playlist_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        playlist_label = tk.Label(
            playlist_frame,
            text="📋 Playlist",
            font=("Arial", 12, "bold"),
            fg='#e94560',
            bg='#1a1a2e'
        )
        playlist_label.pack(anchor='w')
        
        # Playlist listbox with scrollbar
        list_container = tk.Frame(playlist_frame, bg='#1a1a2e')
        list_container.pack(fill='both', expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side='right', fill='y')
        
        self.playlist_box = tk.Listbox(
            list_container,
            bg='#16213e',
            fg='white',
            selectbackground='#e94560',
            selectforeground='white',
            font=("Arial", 9),
            height=6,
            yscrollcommand=scrollbar.set
        )
        self.playlist_box.pack(fill='both', expand=True)
        scrollbar.config(command=self.playlist_box.yview)
        
        # Double-click to play selected track
        self.playlist_box.bind('<Double-1>', self.play_selected)
        
        # Playlist control buttons
        playlist_btn_frame = tk.Frame(playlist_frame, bg='#1a1a2e')
        playlist_btn_frame.pack(fill='x', pady=5)
        
        small_btn_style = {
            'font': ("Arial", 9),
            'bg': '#0f3460',
            'fg': 'white',
            'activebackground': '#e94560',
            'activeforeground': 'white',
            'relief': 'flat',
            'cursor': 'hand2'
        }
        
        self.btn_clear = tk.Button(
            playlist_btn_frame,
            text="🗑 Clear",
            command=self.clear_playlist,
            **small_btn_style
        )
        self.btn_clear.pack(side='left', padx=5)
        
        self.btn_remove = tk.Button(
            playlist_btn_frame,
            text="➖ Remove",
            command=self.remove_selected,
            **small_btn_style
        )
        self.btn_remove.pack(side='left', padx=5)
        
        # Minimize to tray button
        self.btn_tray = tk.Button(
            playlist_btn_frame,
            text="📥 To Tray",
            command=self.hide_to_tray,
            **small_btn_style
        )
        self.btn_tray.pack(side='right', padx=5)
        
    def open_files(self):
        """Open multiple audio files"""
        filetypes = [
            ("Audio files", "*.mp3 *.wav *.ogg *.flac"),
            ("MP3 files", "*.mp3"),
            ("WAV files", "*.wav"),
            ("OGG files", "*.ogg"),
            ("All files", "*.*")
        ]
        
        file_paths = filedialog.askopenfilenames(
            title="Select audio files",
            filetypes=filetypes
        )
        
        if file_paths:
            # Add files to playlist
            for file_path in file_paths:
                if file_path not in self.playlist:
                    self.playlist.append(file_path)
                    # Get duration and show in playlist
                    duration = self.get_audio_duration(file_path)
                    file_name = os.path.basename(file_path)
                    display_text = f"{file_name} [{self.format_time(duration)}]"
                    self.playlist_box.insert(tk.END, display_text)
            
            # If nothing is playing, start first added file
            if not self.is_playing:
                self.current_index = len(self.playlist) - len(file_paths)
                self.play_current()
                
            self.update_track_label()
            
    def play_current(self):
        """Play the current track from playlist"""
        if self.playlist and 0 <= self.current_index < len(self.playlist):
            self.current_file = self.playlist[self.current_index]
            file_name = os.path.basename(self.current_file)
            
            # Get duration
            self.current_duration = self.get_audio_duration(self.current_file)
            
            self.file_label.config(text=f"🎵 {file_name}")
            
            try:
                pygame.mixer.music.load(self.current_file)
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                self.btn_play.config(text="⏸")
                self.status_label.config(text="▶ Playing", fg='#00d25b')
                
                # Reset progress
                self.progress_bar['value'] = 0
                
                # Highlight current track
                self.playlist_box.selection_clear(0, tk.END)
                self.playlist_box.selection_set(self.current_index)
                self.playlist_box.see(self.current_index)
                
                self.update_track_label()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to play file:\n{e}")
                
    def play_selected(self, event=None):
        """Play selected track from playlist"""
        selection = self.playlist_box.curselection()
        if selection:
            self.current_index = selection[0]
            self.play_current()
            
    def prev_track(self):
        """Play previous track"""
        if self.playlist:
            self.current_index = (self.current_index - 1) % len(self.playlist)
            self.play_current()
            
    def next_track(self):
        """Play next track"""
        if self.playlist:
            self.current_index = (self.current_index + 1) % len(self.playlist)
            self.play_current()
            
    def rewind(self):
        """Rewind 5 seconds"""
        if self.is_playing and self.current_file:
            current_pos = pygame.mixer.music.get_pos() / 1000
            new_pos = max(0, current_pos - 5)
            pygame.mixer.music.play(start=new_pos)
            
    def forward(self):
        """Forward 5 seconds"""
        if self.is_playing and self.current_file:
            current_pos = pygame.mixer.music.get_pos() / 1000
            new_pos = min(self.current_duration, current_pos + 5)
            if new_pos < self.current_duration:
                pygame.mixer.music.play(start=new_pos)
            else:
                self.next_track()
            
    def check_music_end(self):
        """Check if current track ended and play next"""
        if self.is_playing and not self.is_paused:
            if not pygame.mixer.music.get_busy():
                # Music ended, play next
                if self.current_index < len(self.playlist) - 1:
                    self.current_index += 1
                    self.play_current()
                else:
                    # End of playlist
                    self.is_playing = False
                    self.btn_play.config(text="▶")
                    self.status_label.config(text="⏹ Finished", fg='#0f3460')
                    self.progress_bar['value'] = 100
                    self.time_label.config(
                        text=f"{self.format_time(self.current_duration)} / {self.format_time(self.current_duration)}"
                    )
                        
        self.root.after(500, self.check_music_end)
            
    def play_pause(self):
        """Toggle play/pause"""
        if not self.playlist:
            messagebox.showinfo("Info", "Please select files first!")
            return
            
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.btn_play.config(text="▶")
            self.status_label.config(text="⏸ Paused", fg='#ffc107')
        elif self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.btn_play.config(text="⏸")
            self.status_label.config(text="▶ Playing", fg='#00d25b')
        else:
            self.play_current()
            
    def stop(self):
        """Stop playback"""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.btn_play.config(text="▶")
        self.status_label.config(text="⏹ Stopped", fg='#0f3460')
        self.progress_bar['value'] = 0
        self.time_label.config(text="00:00 / 00:00")
        
    def clear_playlist(self):
        """Clear playlist"""
        self.stop()
        self.playlist.clear()
        self.playlist_box.delete(0, tk.END)
        self.current_index = 0
        self.current_file = None
        self.current_duration = 0
        self.file_label.config(text="No file selected")
        self.update_track_label()
        
    def remove_selected(self):
        """Remove selected track"""
        selection = self.playlist_box.curselection()
        if selection:
            index = selection[0]
            
            if index == self.current_index and self.is_playing:
                self.stop()
                
            del self.playlist[index]
            self.playlist_box.delete(index)
            
            if index < self.current_index:
                self.current_index -= 1
            elif index == self.current_index and self.playlist:
                if self.current_index >= len(self.playlist):
                    self.current_index = len(self.playlist) - 1
                    
            self.update_track_label()
            
    def update_track_label(self):
        """Update track counter"""
        total = len(self.playlist)
        current = self.current_index + 1 if total > 0 else 0
        self.track_label.config(text=f"Track: {current} / {total}")
            
    def change_volume(self, value):
        """Change volume"""
        self.volume = float(value) / 100
        pygame.mixer.music.set_volume(self.volume)
        
        volume_percent = int(float(value))
        
        if hasattr(self, 'volume_label'):
            self.volume_label.config(text=f"{volume_percent}%")
        
        if hasattr(self, 'volume_icon'):
            if volume_percent == 0:
                self.volume_icon.config(text="🔇")
            elif volume_percent < 33:
                self.volume_icon.config(text="🔈")
            elif volume_percent < 66:
                self.volume_icon.config(text="🔉")
            else:
                self.volume_icon.config(text="🔊")
            
    def update_progress(self):
        """Update progress bar with actual duration"""
        if self.is_playing and not self.is_paused:
            try:
                # Get current position in milliseconds
                current_pos_ms = pygame.mixer.music.get_pos()
                
                if current_pos_ms > 0 and self.current_duration > 0:
                    # Convert to seconds
                    current_sec = current_pos_ms / 1000
                    
                    # Calculate progress percentage
                    progress = (current_sec / self.current_duration) * 100
                    progress = min(progress, 100)  # Cap at 100%
                    
                    self.progress_bar['value'] = progress
                    
                    # Update time display
                    self.time_label.config(
                        text=f"{self.format_time(current_sec)} / {self.format_time(self.current_duration)}"
                    )
                    
            except Exception:
                pass
                
        self.root.after(50, self.update_progress)  # Update more frequently for smoother progress
        
    def create_tray_icon(self):
        """Create tray icon"""
        icon_size = 64
        image = Image.new('RGB', (icon_size, icon_size), color='#1a1a2e')
        draw = ImageDraw.Draw(image)
        
        draw.ellipse([16, 32, 32, 48], fill='#e94560')
        draw.rectangle([28, 12, 32, 36], fill='#e94560')
        draw.ellipse([32, 24, 48, 40], fill='#e94560')
        draw.rectangle([44, 4, 48, 28], fill='#e94560')
        
        return image
        
    def hide_to_tray(self):
        """Minimize to tray"""
        self.root.withdraw()
        self.hidden = True
        
        if self.tray_icon is None:
            menu = (
                item('▶ Play/Pause', self.tray_play_pause),
                item('⏹ Stop', self.tray_stop),
                item('⏮ Previous', self.tray_prev),
                item('⏭ Next', self.tray_next),
                pystray.Menu.SEPARATOR,
                item('🔊 Volume +', self.tray_volume_up),
                item('🔉 Volume -', self.tray_volume_down),
                pystray.Menu.SEPARATOR,
                item('🔄 Show Window', self.show_window),
                item('❌ Exit', self.quit_app)
            )
            
            icon_image = self.create_tray_icon()
            self.tray_icon = pystray.Icon(
                "audio_player",
                icon_image,
                "Audio Player",
                menu
            )
            
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
        
    def show_window(self, icon=None, item=None):
        """Show window"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.hidden = False
        
    def tray_play_pause(self, icon=None, item=None):
        self.root.after(0, self.play_pause)
        
    def tray_stop(self, icon=None, item=None):
        self.root.after(0, self.stop)
        
    def tray_prev(self, icon=None, item=None):
        self.root.after(0, self.prev_track)
        
    def tray_next(self, icon=None, item=None):
        self.root.after(0, self.next_track)
        
    def tray_volume_up(self, icon=None, item=None):
        new_volume = min(100, self.volume * 100 + 10)
        self.root.after(0, lambda: self.volume_slider.set(new_volume))
        
    def tray_volume_down(self, icon=None, item=None):
        new_volume = max(0, self.volume * 100 - 10)
        self.root.after(0, lambda: self.volume_slider.set(new_volume))
        
    def quit_app(self, icon=None, item=None):
        """Exit app"""
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        
        if self.tray_icon:
            self.tray_icon.stop()
            
        self.root.quit()
        self.root.destroy()
        sys.exit()
        
    def run(self):
        """Run app"""
        self.root.mainloop()


if __name__ == "__main__":
    player = AudioPlayer()
    player.run()