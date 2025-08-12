# gui.py
# GUI interface for Stock Tracker using Tkinter

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import logging
from datetime import datetime
from typing import Optional
from config import Config
from scheduler import DataScheduler
from database import StockDatabase

class StockTrackerGUI:
    """
    Main GUI application for Stock Tracker
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.scheduler = DataScheduler()
        self.database = StockDatabase()
        self.is_running = False
        
        self.setup_window()
        self.create_widgets()
        self.setup_logging()
        self.update_display()
        
    def setup_window(self):
        """Configure the main window"""
        self.root.title(f"{Config.APP_NAME} v{Config.APP_VERSION}")
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        self.root.minsize(600, 400)
        
        # Center the window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (Config.WINDOW_WIDTH // 2)
        y = (self.root.winfo_screenheight() // 2) - (Config.WINDOW_HEIGHT // 2)
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}+{x}+{y}")
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_main_tab()
        self.create_data_tab()
        self.create_settings_tab()
        self.create_logs_tab()
    
    def create_main_tab(self):
        """Create the main control tab"""
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="Main")
        
        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Stopped", font=("Arial", 12, "bold"))
        self.status_label.pack()
        
        self.market_status_label = ttk.Label(status_frame, text="Market: Unknown")
        self.market_status_label.pack()
        
        self.last_update_label = ttk.Label(status_frame, text="Last Update: Never")
        self.last_update_label.pack()
        
        # Control buttons
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack()
        
        self.start_button = ttk.Button(button_frame, text="Start", command=self.start_tracking)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_tracking, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.collect_now_button = ttk.Button(button_frame, text="Collect Now", command=self.collect_now)
        self.collect_now_button.pack(side=tk.LEFT, padx=5)
        
        # Statistics section
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        stats_inner_frame = ttk.Frame(stats_frame)
        stats_inner_frame.pack(fill=tk.X)
        
        # Left column
        left_stats = ttk.Frame(stats_inner_frame)
        left_stats.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.total_records_label = ttk.Label(left_stats, text="Total Records: 0")
        self.total_records_label.pack(anchor=tk.W)
        
        self.fetch_count_label = ttk.Label(left_stats, text="Fetch Count: 0")
        self.fetch_count_label.pack(anchor=tk.W)
        
        # Right column
        right_stats = ttk.Frame(stats_inner_frame)
        right_stats.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.symbols_count_label = ttk.Label(right_stats, text="Symbols: 0")
        self.symbols_count_label.pack(anchor=tk.E)
        
        self.error_count_label = ttk.Label(right_stats, text="Errors: 0")
        self.error_count_label.pack(anchor=tk.E)
    
    def create_data_tab(self):
        """Create the data viewing tab"""
        data_frame = ttk.Frame(self.notebook)
        self.notebook.add(data_frame, text="Data")
        
        # Symbol selection
        symbol_frame = ttk.Frame(data_frame)
        symbol_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(symbol_frame, text="Symbol:").pack(side=tk.LEFT)
        
        self.symbol_var = tk.StringVar()
        self.symbol_combo = ttk.Combobox(symbol_frame, textvariable=self.symbol_var, width=10)
        self.symbol_combo.pack(side=tk.LEFT, padx=5)
        self.symbol_combo.bind("<<ComboboxSelected>>", self.on_symbol_selected)
        
        ttk.Button(symbol_frame, text="Refresh", command=self.refresh_data).pack(side=tk.LEFT, padx=5)
        
        # Data display
        data_display_frame = ttk.LabelFrame(data_frame, text="Recent Data", padding=5)
        data_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for data display
        columns = ("Timestamp", "Open", "High", "Low", "Close", "Volume")
        self.data_tree = ttk.Treeview(data_display_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        for col in columns:
            self.data_tree.heading(col, text=col)
            if col == "Timestamp":
                self.data_tree.column(col, width=150)
            elif col == "Volume":
                self.data_tree.column(col, width=100)
            else:
                self.data_tree.column(col, width=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(data_display_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        h_scrollbar = ttk.Scrollbar(data_display_frame, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_settings_tab(self):
        """Create the settings tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        
        # Symbols management
        symbols_frame = ttk.LabelFrame(settings_frame, text="Manage Symbols", padding=10)
        symbols_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add symbol section
        add_frame = ttk.Frame(symbols_frame)
        add_frame.pack(fill=tk.X)
        
        ttk.Label(add_frame, text="Add Symbol:").pack(side=tk.LEFT)
        self.new_symbol_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.new_symbol_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(add_frame, text="Add", command=self.add_symbol).pack(side=tk.LEFT)
        
        # Current symbols list
        current_frame = ttk.Frame(symbols_frame)
        current_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        ttk.Label(current_frame, text="Current Symbols:").pack(anchor=tk.W)
        
        symbols_list_frame = ttk.Frame(current_frame)
        symbols_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.symbols_listbox = tk.Listbox(symbols_list_frame, height=6)
        self.symbols_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        symbols_scrollbar = ttk.Scrollbar(symbols_list_frame, orient=tk.VERTICAL, command=self.symbols_listbox.yview)
        symbols_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.symbols_listbox.configure(yscrollcommand=symbols_scrollbar.set)
        
        remove_button_frame = ttk.Frame(current_frame)
        remove_button_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(remove_button_frame, text="Remove Selected", command=self.remove_symbol).pack()
        
        # Options
        options_frame = ttk.LabelFrame(settings_frame, text="Options", padding=10)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.market_hours_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Collect data only during market hours", 
                       variable=self.market_hours_var, command=self.update_market_hours).pack(anchor=tk.W)
        
        # Backfill data
        backfill_frame = ttk.LabelFrame(settings_frame, text="Backfill Data", padding=10)
        backfill_frame.pack(fill=tk.X, padx=5, pady=5)
        
        backfill_control_frame = ttk.Frame(backfill_frame)
        backfill_control_frame.pack(fill=tk.X)
        
        ttk.Label(backfill_control_frame, text="Days:").pack(side=tk.LEFT)
        self.backfill_days_var = tk.StringVar(value="1")
        ttk.Entry(backfill_control_frame, textvariable=self.backfill_days_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(backfill_control_frame, text="Backfill All Symbols", command=self.backfill_data).pack(side=tk.LEFT, padx=5)
    
    def create_logs_tab(self):
        """Create the logs tab"""
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Logs")
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(logs_frame, height=20, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Clear logs button
        ttk.Button(logs_frame, text="Clear Logs", command=self.clear_logs).pack(pady=5)
    
    def setup_logging(self):
        """Setup logging to display in GUI"""
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                
                def append():
                    self.text_widget.insert(tk.END, msg + '\n')
                    self.text_widget.see(tk.END)
                    
                    # Keep only last 1000 lines
                    lines = self.text_widget.get('1.0', tk.END).split('\n')
                    if len(lines) > 1000:
                        self.text_widget.delete('1.0', f'{len(lines)-1000}.0')
                
                # Schedule GUI update
                self.text_widget.after(0, append)
        
        # Add GUI handler to logger
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_handler.setFormatter(formatter)
        
        logger = logging.getLogger()
        logger.addHandler(gui_handler)
    
    def start_tracking(self):
        """Start the data collection"""
        try:
            self.scheduler.start(market_hours_only=self.market_hours_var.get())
            self.is_running = True
            
            # Update button states
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # Update status
            self.status_label.config(text="Running", foreground="green")
            
            logging.info("Stock tracking started from GUI")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start tracking: {e}")
    
    def stop_tracking(self):
        """Stop the data collection"""
        try:
            self.scheduler.stop()
            self.is_running = False
            
            # Update button states
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # Update status
            self.status_label.config(text="Stopped", foreground="red")
            
            logging.info("Stock tracking stopped from GUI")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop tracking: {e}")
    
    def collect_now(self):
        """Manually trigger data collection"""
        def collect():
            try:
                results = self.scheduler.collect_now(force=True)
                success_count = sum(1 for r in results if r.success)
                
                def update_gui():
                    messagebox.showinfo("Collection Complete", 
                                      f"Collected data for {success_count}/{len(results)} symbols")
                    self.update_display()
                
                self.root.after(0, update_gui)
                
            except Exception as e:
                def show_error():
                    messagebox.showerror("Error", f"Collection failed: {e}")
                
                self.root.after(0, show_error)
        
        # Run collection in background thread
        threading.Thread(target=collect, daemon=True).start()
    
    def update_display(self):
        """Update all display elements"""
        try:
            status = self.scheduler.get_status()
            
            # Update status labels
            if status['is_running']:
                self.status_label.config(text="Running", foreground="green")
            else:
                self.status_label.config(text="Stopped", foreground="red")
            
            # Update market status
            market_status = status['market_status']
            if market_status:
                market_text = "OPEN" if market_status.is_open else "CLOSED"
                color = "green" if market_status.is_open else "red"
                self.market_status_label.config(text=f"Market: {market_text}", foreground=color)
            
            # Update statistics
            if status['last_fetch_time']:
                last_update = status['last_fetch_time'].strftime("%H:%M:%S")
                self.last_update_label.config(text=f"Last Update: {last_update}")
            
            self.total_records_label.config(text=f"Total Records: {status['total_records']}")
            self.fetch_count_label.config(text=f"Fetch Count: {status['fetch_count']}")
            self.symbols_count_label.config(text=f"Symbols: {status['symbols_count']}")
            self.error_count_label.config(text=f"Errors: {status['error_count']}")
            
            # Update symbols list
            symbols = self.scheduler.get_symbols()
            self.symbol_combo['values'] = symbols
            self.symbols_listbox.delete(0, tk.END)
            for symbol in symbols:
                self.symbols_listbox.insert(tk.END, symbol)
            
        except Exception as e:
            logging.error(f"Error updating display: {e}")
        
        # Schedule next update
        self.root.after(Config.UPDATE_GUI_INTERVAL, self.update_display)
    
    def on_symbol_selected(self, event):
        """Handle symbol selection in data tab"""
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh data display for selected symbol"""
        symbol = self.symbol_var.get()
        if not symbol:
            return
        
        try:
            # Clear existing data
            for item in self.data_tree.get_children():
                self.data_tree.delete(item)
            
            # Get recent candles for symbol
            candles = self.database.get_candles_for_symbol(symbol, limit=50)
            
            # Display data in reverse chronological order
            for candle in candles:
                values = (
                    candle.timestamp.strftime("%Y-%m-%d %H:%M"),
                    f"{candle.open_price:.2f}",
                    f"{candle.high_price:.2f}",
                    f"{candle.low_price:.2f}",
                    f"{candle.close_price:.2f}",
                    f"{candle.volume:,}"
                )
                self.data_tree.insert("", 0, values=values)  # Insert at top
            
        except Exception as e:
            logging.error(f"Error refreshing data: {e}")
    
    def add_symbol(self):
        """Add a new symbol to track"""
        symbol = self.new_symbol_var.get().strip().upper()
        if not symbol:
            return
        
        if self.scheduler.add_symbol(symbol):
            self.new_symbol_var.set("")
            messagebox.showinfo("Success", f"Added symbol: {symbol}")
            self.update_display()
        else:
            messagebox.showerror("Error", f"Failed to add symbol: {symbol}")
    
    def remove_symbol(self):
        """Remove selected symbol from tracking"""
        selection = self.symbols_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a symbol to remove")
            return
        
        symbol = self.symbols_listbox.get(selection[0])
        
        if messagebox.askyesno("Confirm", f"Remove {symbol} from tracking?"):
            if self.scheduler.remove_symbol(symbol):
                messagebox.showinfo("Success", f"Removed symbol: {symbol}")
                self.update_display()
            else:
                messagebox.showerror("Error", f"Failed to remove symbol: {symbol}")
    
    def update_market_hours(self):
        """Update market hours setting"""
        self.scheduler.set_market_hours_only(self.market_hours_var.get())
    
    def backfill_data(self):
        """Backfill historical data"""
        try:
            days = int(self.backfill_days_var.get())
            
            def backfill():
                try:
                    results = self.scheduler.backfill_all_symbols(days)
                    total = sum(results.values())
                    
                    def show_result():
                        messagebox.showinfo("Backfill Complete", 
                                          f"Backfilled {total} records for {days} days")
                        self.update_display()
                    
                    self.root.after(0, show_result)
                    
                except Exception as e:
                    def show_error():
                        messagebox.showerror("Error", f"Backfill failed: {e}")
                    
                    self.root.after(0, show_error)
            
            # Run in background thread
            threading.Thread(target=backfill, daemon=True).start()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of days")
    
    def clear_logs(self):
        """Clear the log display"""
        self.log_text.delete('1.0', tk.END)
    
    def on_closing(self):
        """Handle application closing"""
        if self.is_running:
            if messagebox.askyesno("Quit", "Data collection is running. Stop and quit?"):
                self.stop_tracking()
                self.root.after(100, self.root.destroy)
        else:
            self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        logging.info("Starting Stock Tracker GUI")
        self.root.mainloop()

def main():
    """Main entry point for GUI"""
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE_PATH) if Config.LOG_TO_FILE else logging.NullHandler(),
            logging.StreamHandler()
        ]
    )
    
    try:
        app = StockTrackerGUI()
        app.run()
    except Exception as e:
        logging.error(f"Failed to start GUI: {e}")
        raise

if __name__ == "__main__":
    main()