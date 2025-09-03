def create_data_tab(self):
    """Create the data viewing tab"""
    data_frame = ttk.Frame(self.notebook)
    self.notebook.add(data_frame, text="Data")
    
    # Control panel
    control_frame = ttk.Frame(data_frame)
    control_frame.pack(fill=tk.X, padx=5, pady=5)
    
    # Symbol selection
    symbol_frame = ttk.Frame(control_frame)
    symbol_frame.pack(side=tk.LEFT, padx=5)
    
    ttk.Label(symbol_frame, text="Symbol:").pack(side=tk.TOP, anchor=tk.W)
    
    self.symbol_var = tk.StringVar()
    self.symbol_combo = ttk.Combobox(symbol_frame, textvariable=self.symbol_var, width=10)
    self.symbol_combo.pack(side=tk.TOP)
    self.symbol_combo.bind("<<ComboboxSelected>>", self.on_symbol_selected)
    
    # Date filter
    date_frame = ttk.Frame(control_frame)
    date_frame.pack(side=tk.LEFT, padx=20)
    
    ttk.Label(date_frame, text="Filter by Date:").pack(side=tk.TOP, anchor=tk.W)
    
    date_input_frame = ttk.Frame(date_frame)
    date_input_frame.pack(side=tk.TOP)
    
    self.date_var = tk.StringVar()
    self.date_entry = ttk.Entry(date_input_frame, textvariable=self.date_var, width=12)
    self.date_entry.pack(side=tk.LEFT)
    self.date_entry.bind("<KeyRelease>", self.on_date_filter_changed)
    
    ttk.Label(date_input_frame, text="(YYYY-MM-DD)").pack(side=tk.LEFT, padx=5)
    
    ttk.Button(date_frame, text="Clear Filter", command=self.clear_date_filter).pack(side=tk.TOP, pady=2)
    
    # Refresh button
    button_frame = ttk.Frame(control_frame)
    button_frame.pack(side=tk.RIGHT, padx=5)
    
    ttk.Button(button_frame, text="Refresh Data", command=self.refresh_data).pack()
    
    # Data display
    data_display_frame = ttk.LabelFrame(data_frame, text="Recent Data", padding=5)
    data_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Create treeview for data display
    columns = ("Timestamp", "Open", "High", "Low", "Close", "Volume", "Avg Price", "Money Flow (K)", "Net MF")
    self.data_tree = ttk.Treeview(data_display_frame, columns=columns, show="headings", height=15)
    
    # Configure columns
    column_widths = {
        "Timestamp": 150,
        "Open": 80,
        "High": 80,
        "Low": 80,
        "Close": 80,
        "Volume": 100,
        "Avg Price": 80,
        "Money Flow (K)": 100,
        "Net MF": 100
    }
    
    for col in columns:
        self.data_tree.heading(col, text=col)
        self.data_tree.column(col, width=column_widths[col])
    
    # Create frame for treeview and scrollbars
    tree_frame = ttk.Frame(data_display_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)
    
    # Scrollbars
    v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
    h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.data_tree.xview)
    self.data_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    
    # Pack treeview and scrollbars
    self.data_tree.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")
    h_scrollbar.grid(row=1, column=0, sticky="ew")
    
    # Configure grid weights
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

def on_date_filter_changed(self, event=None):
    """Handle date filter changes"""
    self.update_data_display()

def clear_date_filter(self):
    """Clear the date filter"""
    self.date_var.set("")
    self.update_data_display()

def calculate_money_flow_data(self, data):
    """Calculate Avg Price, Money Flow, and Net MF for the data"""
    if not data:
        return []
    
    enhanced_data = []
    previous_avg_price = None
    previous_net_mf = None
    current_date = None
    
    for row in data:
        timestamp, open_price, high, low, close, volume = row
        
        # Calculate Avg Price
        avg_price = (high + low) / 2
        
        # Calculate Money Flow (in thousands)
        money_flow = (avg_price * volume) / 1000
        
        # Extract date from timestamp for first entry logic
        row_date = timestamp.split()[0] if ' ' in str(timestamp) else str(timestamp)[:10]
        
        # Calculate Net MF
        if current_date != row_date:
            # First entry of the day
            current_date = row_date
            if close < open_price:
                net_mf = -money_flow
            else:
                net_mf = money_flow
        else:
            # Subsequent entries of the same day
            if previous_avg_price is not None:
                if avg_price > previous_avg_price:
                    net_mf = money_flow
                elif avg_price < previous_avg_price:
                    net_mf = -money_flow
                else:
                    # Equal avg prices - use previous Net MF sign
                    if previous_net_mf >= 0:
                        net_mf = money_flow
                    else:
                        net_mf = -money_flow
            else:
                # Fallback case
                net_mf = money_flow
        
        enhanced_data.append((
            timestamp,
            round(open_price, 2),
            round(high, 2),
            round(low, 2),
            round(close, 2),
            volume,
            round(avg_price, 2),
            round(money_flow, 2),
            round(net_mf, 2)
        ))
        
        previous_avg_price = avg_price
        previous_net_mf = net_mf
    
    return enhanced_data

def update_data_display(self):
    """Update the data display with current filters"""
    # Clear existing data
    for item in self.data_tree.get_children():
        self.data_tree.delete(item)
    
    if not hasattr(self, 'current_data') or not self.current_data:
        return
    
    # Apply date filter if set
    date_filter = self.date_var.get().strip()
    filtered_data = self.current_data
    
    if date_filter:
        try:
            # Validate date format
            from datetime import datetime
            datetime.strptime(date_filter, '%Y-%m-%d')
            
            # Filter data by date
            filtered_data = []
            for row in self.current_data:
                timestamp = str(row[0])
                row_date = timestamp.split()[0] if ' ' in timestamp else timestamp[:10]
                if row_date == date_filter:
                    filtered_data.append(row)
        except ValueError:
            # Invalid date format, show all data
            pass
    
    # Calculate enhanced data with money flow calculations
    enhanced_data = self.calculate_money_flow_data(filtered_data)
    
    # Populate treeview
    for row in enhanced_data:
        self.data_tree.insert("", "end", values=row)

def refresh_data(self):
    """Refresh data for selected symbol"""
    symbol = self.symbol_var.get()
    if not symbol:
        return
    
    try:
        # Fetch data (replace this with your actual data fetching logic)
        # For now, assuming you have a method to get data
        self.current_data = self.fetch_symbol_data(symbol)
        self.update_data_display()
        
        # Update status
        if hasattr(self, 'status_var'):
            self.status_var.set(f"Data refreshed for {symbol}")
            
    except Exception as e:
        if hasattr(self, 'status_var'):
            self.status_var.set(f"Error refreshing data: {str(e)}")

def on_symbol_selected(self, event=None):
    """Handle symbol selection"""
    self.refresh_data()