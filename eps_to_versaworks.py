#!/usr/bin/env python3
"""
EPS to Versaworks Converter

Converts Inkscape-exported EPS files to be compatible with Roland Versaworks
by adding the CutContour spot color using standard PostScript commands.

The CutContour spot color uses 100% Magenta (CMYK = 0, 100, 0, 0) and is
recognized by Versaworks for cut contour lines.

Usage:
    python eps_to_versaworks.py input.eps [-o output.eps]
"""

import sys
import re
import argparse
import subprocess
import platform
from pathlib import Path


# Inkscape executable path based on OS
def get_inkscape_path():
    """Get the appropriate Inkscape executable path for the current OS."""
    system = platform.system().lower()
    
    if system == 'windows':
        # Common Windows paths for Inkscape
        possible_paths = [
            r'C:\Program Files\Inkscape\bin\inkscape.exe',
            r'C:\Program Files (x86)\Inkscape\bin\inkscape.exe',
            'inkscape.exe'  # If in PATH
        ]
    elif system == 'darwin':  # macOS
        possible_paths = [
            '/Applications/Inkscape.app/Contents/MacOS/inkscape',
            '/usr/local/bin/inkscape',
            'inkscape'  # If in PATH
        ]
    else:  # Linux and other Unix-like systems
        possible_paths = [
            '/usr/bin/inkscape',
            '/usr/local/bin/inkscape', 
            'inkscape'  # If in PATH
        ]
    
    # Check which path exists and is executable
    for path in possible_paths:
        try:
            # Try to run inkscape --version to verify it works
            result = subprocess.run([path, '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            if result.returncode == 0:
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    # Fallback to 'inkscape' in PATH
    return 'inkscape'


INKSCAPE_PATH = get_inkscape_path()


def is_svg_file(file_path):
    """Check if a file is an SVG file by examining its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read first few lines to check for SVG markers
            content = f.read(1024)
            return '<svg' in content.lower() or content.strip().startswith('<?xml')
    except (UnicodeDecodeError, OSError):
        # Try with different encoding or check by extension
        return str(file_path).lower().endswith('.svg')


def convert_svg_to_eps(svg_path, eps_path):
    """Convert SVG to EPS using Inkscape command line."""
    cmd = [
        INKSCAPE_PATH,
        str(svg_path),
        '-o', str(eps_path),
        '--export-text-to-path',
        '--export-ps-level=3'
    ]
    
    try:
        print("Converting SVG to EPS using Inkscape...")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print("Error: Inkscape conversion failed", file=sys.stderr)
            print(f"stderr: {result.stderr}", file=sys.stderr)
            return False
        
        if result.stderr:
            print(f"Inkscape warnings: {result.stderr}", file=sys.stderr)
        
        print(f"Successfully converted SVG to EPS: {eps_path}")
        return True
        
    except subprocess.TimeoutExpired:
        print("Error: Inkscape conversion timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"Error: Inkscape not found at: {INKSCAPE_PATH}", file=sys.stderr)
        print("Please ensure Inkscape is installed and accessible", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error during SVG conversion: {e}", file=sys.stderr)
        return False


class EPSToVersaworksConverter:
    """Converter for EPS files to Versaworks-compatible format."""
    
    # CutContour spot color: 100% Magenta in CMYK
    CUTCONTOUR_CMYK = (0, 100, 0, 0)  # C, M, Y, K as percentages
    
    # Hairline stroke width (0.25 points = Illustrator hairline)
    HAIRLINE_WIDTH = 0.25
    
    def __init__(self, input_file, output_file=None, stroke_width=None):
        """Initialize converter with input/output files."""
        self.original_input_file = Path(input_file)
        self.input_file = Path(input_file)
        self.is_svg_input = False
        self.intermediate_eps = None
        
        # Check if input is SVG and handle accordingly
        if is_svg_file(self.input_file):
            self.is_svg_input = True
            # Create intermediate EPS filename
            self.intermediate_eps = self.input_file.parent / f"{self.input_file.stem}.intermediate.eps"
            self.input_file = self.intermediate_eps
            print(f"Detected SVG input: {self.original_input_file}")
        
        if output_file:
            self.output_file = Path(output_file)
        else:
            stem = self.original_input_file.stem
            if self.is_svg_input:
                suffix = '.eps'
            else:
                suffix = self.input_file.suffix
            self.output_file = self.input_file.parent / f"{stem}_versaworks{suffix}"
        
        self.stroke_width = stroke_width if stroke_width else self.HAIRLINE_WIDTH
        
    def read_file(self):
        """Read the input EPS file."""
        try:
            with open(self.input_file, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {self.input_file}: {e}", file=sys.stderr)
            sys.exit(1)
    
    def write_file(self, content):
        """Write the output EPS file."""
        try:
            with open(self.output_file, 'w', encoding='latin-1') as f:
                f.write(content)
            print(f"Successfully created: {self.output_file}")
        except Exception as e:
            print(f"Error writing {self.output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    
    def add_header_definitions(self, content):
        """
        Add CutContour spot color definitions to the DSC header.
        
        These DSC (Document Structuring Convention) comments inform PostScript
        interpreters about custom colors used in the document.
        """
        lines = content.split('\n')
        new_lines = []
        added = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Add after %%BoundingBox or %%LanguageLevel, before %%EndComments
            if not added and line.startswith(('%%BoundingBox:', '%%LanguageLevel:')):
                # Look ahead to make sure we haven't already added it
                if not any('%%DocumentCustomColors:' in line_text for line_text in lines[i:i+5]):
                    new_lines.append('%%DocumentCustomColors: (CutContour)')
                    # CMYK values in 0-1 scale for DSC comment
                    c, m, y, k = [v/100.0 for v in self.CUTCONTOUR_CMYK]
                    new_lines.append(f'%%CMYKCustomColor: {c:.2f} {m:.2f} {y:.2f} {k:.2f} (CutContour)')
                    added = True
        
        return '\n'.join(new_lines)
    
    def add_spot_color_support(self, content):
        """
        Add PostScript Level 2 spot color support to the prolog.
        
        Uses standard PostScript findcmykcustomcolor and setcustomcolor operators
        which are the industry-standard way to define spot colors.
        """
        # Find %%EndProlog
        prolog_end = content.find('%%EndProlog')
        
        if prolog_end == -1:
            print("Warning: %%EndProlog not found, adding after prolog dict", file=sys.stderr)
            # Try to find end of prolog dict
            dict_end = content.find('%%BeginSetup')
            if dict_end == -1:
                print("Error: Cannot find suitable location for spot color code", file=sys.stderr)
                return content
            prolog_end = dict_end
        
        # PostScript code using standard operators
        # CMYK values as 0-1 scale (0, 1.0, 0, 0 for 100% Magenta)
        c, m, y, k = [v/100.0 for v in self.CUTCONTOUR_CMYK]
        
        spot_color_code = f"""
% CutContour Spot Color Support (PostScript Level 2)
% Use findcmykcustomcolor and setcustomcolor for spot color definition

% Check if spot color operators are available, define if not
/findcmykcustomcolor where {{
  pop  % Operator exists, use it
}} {{
  % Fallback definition for Level 1 or if not available
  /findcmykcustomcolor {{
    5 array astore  % Store C, M, Y, K, name as array
  }} def
}} ifelse

/setcustomcolor where {{
  pop  % Operator exists, use it
}} {{
  % Fallback: convert to CMYK
  /setcustomcolor {{
    exch aload pop pop  % Get C, M, Y, K from array (discard name)
    4 {{
      4 index mul 4 1 roll  % Multiply each component by tint value
    }} repeat
    5 -1 roll pop  % Remove tint value
    setcmykcolor
  }} def
}} ifelse

% Define the CutContour spot color
% Format: C M Y K (ColorName) findcmykcustomcolor
/CutContourColor {{
  {c} {m} {y} {k} (CutContour) findcmykcustomcolor
}} def

% Set CutContour for stroking with full tint (100%)
/SetCutContourStroke {{
  CutContourColor 1.0 setcustomcolor
}} def

% Set hairline stroke width  
/SetHairlineStroke {{
  {self.stroke_width} setlinewidth
}} def

"""

        # Insert before %%EndProlog
        content = content[:prolog_end] + spot_color_code + content[prolog_end:]
        
        return content
    
    def replace_stroke_commands(self, content):
        """
        Replace stroke color commands with CutContour spot color.
        
        This modifies the page content to use the CutContour spot color
        for all stroke operations.
        """
        lines = content.split('\n')
        new_lines = []
        in_page = False
        
        for line in lines:
            # Track page boundaries
            if '%%Page:' in line or '%%BeginPageSetup' in line:
                in_page = True
                new_lines.append(line)
                continue
            
            if '%%Trailer' in line or '%%EOF' in line:
                in_page = False
                new_lines.append(line)
                continue
            
            if not in_page:
                new_lines.append(line)
                continue
            
            # Remove/replace color setting commands that precede strokes
            
            # RGB: "0.5 0.5 0.5 rg" or "setrgbcolor"
            if re.match(r'^\s*[\d.]+\s+[\d.]+\s+[\d.]+\s+(rg|setrgbcolor)\s*$', line):
                continue  # Skip this line
            
            # CMYK: "0 0 0 1 setcmykcolor"
            if re.match(r'^\s*[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+setcmykcolor\s*$', line):
                continue
            
            # Gray: "0.5 g" or "setgray"
            if re.match(r'^\s*[\d.]+\s+(g|setgray)\s*$', line):
                continue
            
            # Line width: "1.5 w" or "setlinewidth"
            if re.match(r'^\s*[\d.]+\s+(w|setlinewidth)\s*$', line):
                # Replace with hairline
                new_lines.append('SetHairlineStroke')
                continue
            
            # Check if line contains stroke commands (S or stroke)
            # Can be standalone or at end of line with other path commands
            # Match patterns: "...m 10 20 l S Q" or just "S" or "stroke"
            if re.search(r'\s(S|stroke)(\s|$)', line):
                # Split the line at the stroke command
                # Replace "S" or "stroke" with color+width+stroke
                modified_line = re.sub(
                    r'(\s)(S|stroke)(\s)',
                    r'\1SetCutContourStroke SetHairlineStroke \2\3',
                    line
                )
                # Handle end of line case
                modified_line = re.sub(
                    r'(\s)(S|stroke)$',
                    r'\1SetCutContourStroke SetHairlineStroke \2',
                    modified_line
                )
                new_lines.append(modified_line)
                continue
            
            # Standalone stroke command on its own line
            if re.match(r'^\s*(S|stroke)\s*$', line):
                # Before stroking, set the CutContour color and hairline width
                new_lines.append('SetCutContourStroke')
                new_lines.append('SetHairlineStroke')
                new_lines.append(line)
                continue
            
            # Keep all other lines
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def convert(self):
        """
        Perform the complete conversion.
        
        Returns:
            bool: True if successful
        """
        print(f"Converting: {self.original_input_file}")
        print(f"Output: {self.output_file}")
        
        # Handle SVG input conversion first
        if self.is_svg_input:
            if not convert_svg_to_eps(self.original_input_file, self.intermediate_eps):
                return False
        
        # Read input (now guaranteed to be EPS)
        content = self.read_file()
        
        # Validate EPS file
        if not content.startswith('%!PS-Adobe'):
            print("Error: Not a valid PostScript/EPS file", file=sys.stderr)
            return False
        
        # Warn if CutContour already present
        if 'CutContour' in content:
            print("Warning: File already contains 'CutContour'")
            response = input("Continue? (y/n): ")
            if response.lower() != 'y':
                return False
        
        # Apply transformations
        print("  [1/3] Adding DSC header definitions...")
        content = self.add_header_definitions(content)
        
        print("  [2/3] Adding spot color PostScript support...")
        content = self.add_spot_color_support(content)
        
        print("  [3/3] Replacing stroke commands with CutContour...")
        content = self.replace_stroke_commands(content)
        
        # Write output
        self.write_file(content)
        
        print("\nConversion complete!")
        print(f"The output file uses CutContour spot color ({self.CUTCONTOUR_CMYK[1]}% Magenta)")
        print(f"with hairline stroke width ({self.stroke_width} pt)")
        
        # Clean up intermediate EPS file if it was created from SVG
        if self.is_svg_input and self.intermediate_eps and self.intermediate_eps.exists():
            try:
                self.intermediate_eps.unlink()
                print(f"Cleaned up intermediate file: {self.intermediate_eps}")
            except Exception as e:
                print(f"Warning: Could not remove intermediate file {self.intermediate_eps}: {e}", file=sys.stderr)
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert SVG or EPS files to Versaworks-compatible format with CutContour spot color',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.eps
  %(prog)s input.svg
  %(prog)s input.eps -o output_cutcontour.eps
  %(prog)s input.svg -o cutlines.eps
  %(prog)s input.eps --stroke-width 0.5

SVG files are automatically detected and converted to EPS using Inkscape.
The CutContour spot color (100%% Magenta) will be applied to all strokes.
"""
    )
    
    parser.add_argument('input', help='Input SVG or EPS file (SVG files converted automatically using Inkscape)')
    parser.add_argument('-o', '--output', help='Output EPS file (default: input_versaworks.eps)')
    parser.add_argument('-w', '--stroke-width', type=float, 
                        help='Stroke width in points (default: 0.25)')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0.0')
    
    args = parser.parse_args()
    
    # Create and run converter
    converter = EPSToVersaworksConverter(args.input, args.output, args.stroke_width)
    success = converter.convert()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
