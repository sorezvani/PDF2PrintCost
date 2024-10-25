import os
import json
import random
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pypdf
from main import calculate_grayscale_coverage , calculate_color_coverage,get_pdf_page_count

class PrinterTab:
    def __init__(self, parent):
        self.parent = parent
        self.printers = self.load_printers()

        # Printer selection UI components
        self.printer_listbox = tk.Listbox(parent, height=10, width=20)
        self.printer_listbox.grid(row=1, column=0, rowspan=6, padx=10, pady=10, sticky=tk.N)
        self.printer_listbox.bind("<<ListboxSelect>>", self.on_printer_select)

        # Printer details fields
        self.printer_name_var = tk.StringVar()
        self.is_color_var = tk.BooleanVar()

        ttk.Label(parent, text="Printer Name:").grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(parent, textvariable=self.printer_name_var, width=25).grid(row=0, column=1, columnspan=4, padx=5, pady=5)

        ttk.Checkbutton(parent, text="Is Color Printer?", variable=self.is_color_var, command=self.toggle_color_fields).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Buttons for add, delete, update
        ttk.Button(parent, text="Add Printer", command=self.add_printer).grid(row=0, column=5, padx=10)
        ttk.Button(parent, text="Delete Printer", command=self.delete_printer).grid(row=1, column=5, padx=10)
        ttk.Button(parent, text="Update Printer", command=self.update_printer).grid(row=2, column=5, padx=10)

        # Ink price/yield fields (color or grayscale)
        self.ink_vars = {
            'Cyan': {'price': tk.StringVar(), 'yield': tk.StringVar()},
            'Magenta': {'price': tk.StringVar(), 'yield': tk.StringVar()},
            'Yellow': {'price': tk.StringVar(), 'yield': tk.StringVar()},
            'Black': {'price': tk.StringVar(), 'yield': tk.StringVar()}
        }

        self.ink_labels_entries = {}
        colors = ['Cyan', 'Magenta', 'Yellow', 'Black']
        for idx, color in enumerate(colors):
            lbl_price = ttk.Label(parent, text=f"{color} Price:")
            lbl_price.grid(row=2 + idx, column=1, sticky=tk.E, padx=(5, 0), pady=2)
            entry_price = ttk.Entry(parent, textvariable=self.ink_vars[color]['price'], width=10)
            entry_price.grid(row=2 + idx, column=2, padx=(0, 5), pady=2)

            lbl_yield = ttk.Label(parent, text=f"{color} Yield:")
            lbl_yield.grid(row=2 + idx, column=3, sticky=tk.E, padx=(5, 0), pady=2)
            entry_yield = ttk.Entry(parent, textvariable=self.ink_vars[color]['yield'], width=10)
            entry_yield.grid(row=2 + idx, column=4, padx=(0, 5), pady=2)

            self.ink_labels_entries[color] = [(lbl_price, entry_price), (lbl_yield, entry_yield)]

        # Initially hide color fields
        self.toggle_color_fields()

        # Load existing printers into listbox
        self.refresh_printer_listbox()

    def on_printer_select(self, event):
        """Handle listbox selection and display selected printer details."""
        selected = self.printer_listbox.curselection()
        if selected:
            printer_name = self.printer_listbox.get(selected[0])
            self.display_printer_details(printer_name)
        else:
            self.clear_fields()

    def display_printer_details(self, printer_name):
        """Display the details of the selected printer."""
        printer_info = self.printers[printer_name]
        self.printer_name_var.set(printer_name)
        self.is_color_var.set(printer_info['is_color'])

        # Set ink price and yield values
        for color, info in printer_info['inks'].items():
            self.ink_vars[color]['price'].set(info['price'])
            self.ink_vars[color]['yield'].set(info['yield'])

        # Update color fields visibility
        self.toggle_color_fields()

    def clear_fields(self):
        """Clear all input fields."""
        self.printer_name_var.set("")
        self.is_color_var.set(False)
        for color in self.ink_vars:
            self.ink_vars[color]['price'].set("")
            self.ink_vars[color]['yield'].set("")

    def toggle_color_fields(self):
        """Show or hide color fields based on whether the printer is color or grayscale."""
        is_color = self.is_color_var.get()
        colors = ['Cyan', 'Magenta', 'Yellow']

        for color in colors:
            for lbl, entry in self.ink_labels_entries[color]:
                if is_color:
                    lbl.grid()
                    entry.grid()
                else:
                    lbl.grid_remove()
                    entry.grid_remove()

    def add_printer(self):
        """Add a new printer based on user input."""
        printer_name = self.printer_name_var.get().strip()
        is_color = self.is_color_var.get()

        if not printer_name:
            messagebox.showerror("Error", "Printer name is required.")
            return

        if printer_name in self.printers:
            messagebox.showerror("Error", "Printer already exists.")
            return

        # Collect ink data
        ink_data = {color: {
            'price': float(self.ink_vars[color]['price'].get()) if self.ink_vars[color]['price'].get() else 0,
            'yield': int(self.ink_vars[color]['yield'].get()) if self.ink_vars[color]['yield'].get() else 0
        } for color in self.ink_vars}

        # Add the printer
        self.printers[printer_name] = {'is_color': is_color, 'inks': ink_data}
        self.save_printers()
        self.refresh_printer_listbox()

    def delete_printer(self):
        """Delete the selected printer."""
        selected = self.printer_listbox.curselection()
        if selected:
            printer_name = self.printer_listbox.get(selected[0])
            del self.printers[printer_name]
            self.save_printers()
            self.refresh_printer_listbox()
            self.clear_fields()
        else:
            messagebox.showerror("Error", "No printer selected.")

    def update_printer(self):
        """Update the selected printer with the current input values."""
        selected = self.printer_listbox.curselection()
        if not selected:
            messagebox.showerror("Error", "No printer selected.")
            return

        printer_name = self.printer_listbox.get(selected[0])
        is_color = self.is_color_var.get()

        # Collect ink data
        ink_data = {color: {
            'price': float(self.ink_vars[color]['price'].get()) if self.ink_vars[color]['price'].get() else 0,
            'yield': int(self.ink_vars[color]['yield'].get()) if self.ink_vars[color]['yield'].get() else 0
        } for color in self.ink_vars}

        # Update the printer
        self.printers[printer_name] = {'is_color': is_color, 'inks': ink_data}
        self.save_printers()
        self.refresh_printer_listbox()

    def load_printers(self):
        """Load printers from a JSON file."""
        if os.path.exists('printers.json'):
            with open('printers.json', 'r') as file:
                return json.load(file)
        return {}

    def save_printers(self):
        """Save printers to a JSON file."""
        with open('printers.json', 'w') as file:
            json.dump(self.printers, file, indent=4)

    def refresh_printer_listbox(self):
        """Refresh the printer listbox with current printers."""
        self.printer_listbox.delete(0, tk.END)
        for printer in self.printers:
            self.printer_listbox.insert(tk.END, printer)

class PaperTab:
    def __init__(self, parent):
        self.parent = parent
        self.papers = self.load_papers()

        # Predefined paper sizes
        self.predefined_papers = ['A4', 'A5']
        self.prices_vars = {paper: tk.StringVar() for paper in self.predefined_papers}

        # Paper price fields
        for idx, paper in enumerate(self.predefined_papers):
            ttk.Label(parent, text=f"{paper} Price:").grid(row=idx, column=1, padx=5, pady=5, sticky=tk.W)
            ttk.Entry(parent, textvariable=self.prices_vars[paper], width=10).grid(row=idx, column=2, padx=(0, 5), pady=2)

        # Load prices into entry fields
        self.load_prices()

        # Buttons for save prices
        ttk.Button(parent, text="Save Prices", command=self.save_prices).grid(row=0, column=5, padx=10)
        ttk.Button(parent, text="Load Prices", command=self.load_prices).grid(row=1, column=5, padx=10)

    def load_prices(self):
        """Load predefined paper prices into entry fields."""
        for paper in self.predefined_papers:
            self.prices_vars[paper].set(self.papers.get(paper, ''))

    def save_prices(self):
        """Save prices of predefined paper sizes."""
        for paper in self.predefined_papers:
            try:
                price = float(self.prices_vars[paper].get())
                if price < 0:
                    raise ValueError("Price must be non-negative.")
                self.papers[paper] = price
            except ValueError:
                messagebox.showerror("Error", f"Invalid price for {paper}. Please enter a valid number.")
                return

        # Save to JSON
        self.save_papers()
        messagebox.showinfo("Success", "Paper prices saved successfully.")

    def load_papers(self):
        """Load papers from a JSON file."""
        if os.path.exists('papers.json'):
            with open('papers.json', 'r') as file:
                return json.load(file)
        return {}

    def save_papers(self):
        """Save papers to a JSON file."""
        with open('papers.json', 'w') as file:
            json.dump(self.papers, file, indent=4)

class CostTab:
    def __init__(self, parent):
        self.parent = parent
        self.printers = self.load_printers()
        self.paper = self.load_paper()

        # PDF file path
        self.pdf_path_var = tk.StringVar()
        ttk.Label(parent, text="PDF File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(parent, textvariable=self.pdf_path_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(parent, text="Browse", command=self.browse_pdf).grid(row=0, column=2, padx=5, pady=5)

        # Print mode selection
        self.print_mode_var = tk.StringVar(value="grayscale")
        ttk.Label(parent, text="Print Mode:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(parent, text="Grayscale", variable=self.print_mode_var, value="grayscale").grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(parent, text="Color", variable=self.print_mode_var, value="color").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        self.print_double = tk.StringVar(value="double side")
        ttk.Label(parent, text="Print Mode:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(parent, text="double", variable=self.print_double, value="double").grid(row=2, column=1,sticky=tk.W,padx=5, pady=5)

        # Calculate Cost Button
        ttk.Button(parent, text="Calculate Cost", command=self.show_costs).grid(row=1, column=3, padx=5, pady=5)

        # Printer cost output
        self.cost_text = tk.Text(parent, height=15, width=60, state="disabled")
        self.cost_text.grid(row=3, column=0, columnspan=4, padx=10, pady=10)

    def browse_pdf(self):
        """Allow the user to select a PDF file."""
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.pdf_path_var.set(file_path)

    def show_costs(self):
        """Calculate and display the cost for each printer based on the selected mode."""
        pdf_path = self.pdf_path_var.get()
        if not pdf_path:
            messagebox.showerror("Error", "Please select a PDF file.")
            return

        # Clear the text area
        self.cost_text.configure(state="normal")
        self.cost_text.delete(1.0, tk.END)

        print_mode = self.print_mode_var.get()
        if print_mode == "color":
            coverage_function = self.calculate_color_coverage
        else:
            coverage_function = self.calculate_grayscale_coverage

        page_mode = self.print_double.get()
        pages = get_pdf_page_count(pdf_path)
        if page_mode == "double":
            cost_page = (-1*(-1*pages // 2)) * self.paper.get("A4")
        else:
            cost_page = pages * self.paper.get("A4")

        cost = cost_page
        self.cost_text.insert(tk.END, f"Printer: paper cost\n")
        self.cost_text.insert(tk.END, f"Estimated Cost: {cost:.2f}\n\n")

        # Display costs for each printer
        for printer_name, printer_info in self.printers.items():
            if print_mode == "color" and not printer_info["is_color"]:
                continue  # Skip grayscale printers if color is selected

            coverage = coverage_function(pdf_path)
            cost = self.calculate_cost(printer_info, coverage)
            self.cost_text.insert(tk.END, f"Printer: {printer_name}\n")
            self.cost_text.insert(tk.END, f"Estimated Cost: {cost:.2f}\n\n")

        self.cost_text.configure(state="disabled")

    def calculate_color_coverage(self, pdf_path):
        """Calculate color coverage for the entire PDF (stub function)."""
        # Stub: Return an arbitrary coverage value (in percentages) for demonstration.
        x = calculate_color_coverage(pdf_path)
        for color , cov in x.items():
            x[color] = cov/5
        return x

    def calculate_grayscale_coverage(self, pdf_path):
        """Calculate grayscale coverage for the entire PDF (stub function)."""
        # Stub: Return an arbitrary coverage value (in percentage) for demonstration.
        x = calculate_grayscale_coverage(pdf_path)
        x /= 5
        return {"Black" : x}

    def calculate_cost(self, printer_info, coverage):
        """Calculate the estimated printing cost based on coverage and printer ink yields."""
        total_cost = 0
        for color, usage in coverage.items():
            ink = printer_info["inks"].get(color)
            if ink and ink["yield"] > 0:  # Avoid division by zero
                cost_per_page = ink["price"] / ink["yield"]
                cost = cost_per_page * usage
                total_cost += cost
        return total_cost

    def load_printers(self):
        """Load printers from a JSON file."""
        if os.path.exists("printers.json"):
            with open("printers.json", "r") as file:
                return json.load(file)
        return {}

    def load_paper(self):
        """Load paper from a JSON file."""
        if os.path.exists("papers.json"):
            with open("papers.json", "r") as file:
                return json.load(file)
        return {}

# Main GUI Setup
def main_gui():
    root = tk.Tk()
    root.title("Printer Manager")

    tab_control = ttk.Notebook(root)

    printer_tab = ttk.Frame(tab_control)
    paper_tab = ttk.Frame(tab_control)
    cost_tab = ttk.Frame(tab_control)

    tab_control.add(printer_tab, text='Printer')
    tab_control.add(paper_tab, text='Paper')
    tab_control.add(cost_tab, text="cost")
    tab_control.pack(expand=1, fill='both')

    app = PrinterTab(printer_tab)
    PaperTab(paper_tab)
    CostTab(cost_tab)

    root.mainloop()


if __name__ == "__main__":
    main_gui()
