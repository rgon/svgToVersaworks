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
import tempfile
import xml.etree.ElementTree as ET
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


def find_cut_group_in_svg(svg_path):
    """Find if SVG contains a 'cut' group/layer (case-insensitive).
    
    Returns:
        tuple: (has_cut_group, cut_group_ids) where cut_group_ids is a list of element IDs
    """
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        cut_group_ids = []
        
        # Search for groups with 'cut' in id or label (case-insensitive)
        for elem in root.iter():
            # Check id attribute
            elem_id = elem.get('id', '')
            # Check inkscape:label attribute
            elem_label = elem.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
            
            if 'cut' in elem_id.lower() or 'cut' in elem_label.lower():
                # Found a cut group/layer
                cut_group_ids.append(elem_id if elem_id else elem_label)
        
        return len(cut_group_ids) > 0, cut_group_ids
    except Exception as e:
        print(f"Warning: Could not parse SVG for cut group detection: {e}", file=sys.stderr)
        return False, []


def create_svg_with_only_cut_group(svg_path, output_path):
    """Create a new SVG with only the cut group visible."""
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Find and mark all non-cut elements for removal
        elements_to_remove = []
        cut_group_found = False
        
        for elem in root.iter():
            elem_id = elem.get('id', '')
            elem_label = elem.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
            
            # Check if this is a cut group
            is_cut_group = 'cut' in elem_id.lower() or 'cut' in elem_label.lower()
            
            if is_cut_group:
                cut_group_found = True
                # Make sure it's visible
                if 'style' in elem.attrib:
                    style = elem.attrib['style']
                    style = re.sub(r'display:\s*none', 'display:inline', style)
                    elem.attrib['style'] = style
            else:
                # Mark top-level children of root for potential removal
                if elem.tag.endswith('}g') or elem.tag.endswith('}path') or elem.tag.endswith('}rect') or elem.tag.endswith('}circle'):
                    # Check if this element is a direct child of root (not nested in cut group)
                    if elem in list(root):
                        elements_to_remove.append(elem)
        
        # Remove non-cut elements
        for elem in elements_to_remove:
            # Check if element is truly outside cut group
            elem_id = elem.get('id', '')
            elem_label = elem.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
            if 'cut' not in elem_id.lower() and 'cut' not in elem_label.lower():
                root.remove(elem)
        
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        return cut_group_found
    except Exception as e:
        print(f"Error creating cut-only SVG: {e}", file=sys.stderr)
        return False


def create_svg_without_cut_group(svg_path, output_path):
    """Create a new SVG with the cut group removed/hidden."""
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Find and remove cut groups
        elements_to_remove = []
        
        for elem in root.iter():
            elem_id = elem.get('id', '')
            elem_label = elem.get('{http://www.inkscape.org/namespaces/inkscape}label', '')
            
            # Check if this is a cut group
            is_cut_group = 'cut' in elem_id.lower() or 'cut' in elem_label.lower()
            
            if is_cut_group and elem in list(root):
                elements_to_remove.append(elem)
        
        # Remove cut elements
        for elem in elements_to_remove:
            root.remove(elem)
        
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        return True
    except Exception as e:
        print(f"Error creating print-only SVG: {e}", file=sys.stderr)
        return False


def convert_svg_to_eps(svg_path, eps_path, export_id=None):
    """Convert SVG to EPS using Inkscape command line.
    
    Args:
        svg_path: Path to input SVG
        eps_path: Path to output EPS
        export_id: Optional ID of specific element to export
    """
    cmd = [
        INKSCAPE_PATH,
        str(svg_path),
        '-o', str(eps_path),
        '--export-text-to-path',
        '--export-ps-level=3'
    ]
    
    if export_id:
        cmd.extend(['--export-id', export_id, '--export-id-only'])
    
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


def validate_eps_with_gs(eps_path):
    """Validate EPS file using Ghostscript.
    
    Returns:
        bool: True if valid
    """
    try:
        cmd = [
            'gs',
            '-dNOPAUSE',
            '-dBATCH',
            '-dSAFER',
            '-sDEVICE=nullpage',
            str(eps_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Warning: Ghostscript validation failed for {eps_path}", file=sys.stderr)
            print(f"stderr: {result.stderr}", file=sys.stderr)
            return False
        
        print(f"✓ Validated EPS with Ghostscript: {eps_path}")
        return True
        
    except subprocess.TimeoutExpired:
        print("Warning: Ghostscript validation timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Warning: Ghostscript (gs) not found, skipping validation", file=sys.stderr)
        return True  # Don't fail if gs is not available
    except Exception as e:
        print(f"Warning: Ghostscript validation error: {e}", file=sys.stderr)
        return True  # Don't fail on validation errors


class EPSToVersaworksConverter:
    """Converter for EPS files to Versaworks-compatible format."""
    
    # CutContour spot color: 100% Magenta in CMYK
    CUTCONTOUR_CMYK = (0, 100, 0, 0)  # C, M, Y, K as percentages
    
    # Hairline stroke width (0.25 points = Illustrator hairline)
    HAIRLINE_WIDTH = 0.25
    
    def __init__(self, input_file, output_file=None, stroke_width=None, convert_everything=False):
        """Initialize converter with input/output files."""
        self.original_input_file = Path(input_file)
        self.input_file = Path(input_file)
        self.is_svg_input = False
        self.intermediate_eps = None
        self.convert_everything = convert_everything
        self.has_cut_layer = False
        self.cut_eps = None
        self.print_eps = None
        
        # Check if input is SVG and handle accordingly
        if is_svg_file(self.input_file):
            self.is_svg_input = True
            # Create intermediate EPS filename
            self.intermediate_eps = self.input_file.parent / f"{self.input_file.stem}.intermediate.eps"
            self.input_file = self.intermediate_eps
            print(f"Detected SVG input: {self.original_input_file}")
            
            # Check for cut layer if not converting everything
            if not convert_everything:
                has_cut, cut_ids = find_cut_group_in_svg(self.original_input_file)
                self.has_cut_layer = has_cut
                if has_cut:
                    print(f"Found cut layer(s) in SVG: {', '.join(cut_ids)}")
        
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
    
    def merge_eps_files(self, print_eps_path, cut_eps_path, output_path):
        """Merge print and cut EPS files maintaining alignment.
        
        Strategy: Extract page content from both files and combine them in a single EPS.
        The print content is drawn first, then the cut content on top.
        """
        try:
            # Read both EPS files
            with open(print_eps_path, 'r', encoding='latin-1') as f:
                print_content = f.read()
            
            with open(cut_eps_path, 'r', encoding='latin-1') as f:
                cut_content = f.read()
            
            # Extract bounding box from cut file (use the larger one if needed)
            bbox_match = re.search(r'%%BoundingBox:\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', cut_content)
            if not bbox_match:
                print("Error: Could not find BoundingBox in cut EPS", file=sys.stderr)
                return False
            
            # Extract ONLY the drawing commands (after %%EndPageSetup, before showpage/%%Trailer)
            # We need to skip the initial clipping and transformation that's specific to each export
            
            # Print page: get commands but skip the first 'q...rectclip' and transformation
            print_full_match = re.search(r'%%EndPageSetup\s*\n(.*?)\s*showpage', print_content, re.DOTALL)
            if not print_full_match:
                print("Warning: Could not extract print drawing commands", file=sys.stderr)
                print_drawing_commands = ""
            else:
                print_full = print_full_match.group(1)
                # Skip initial setup (q...rectclip and transformation matrix lines)
                # Look for the first actual drawing command after setup
                lines = print_full.split('\n')
                # Skip lines until we pass the initial 'cm q' (coordinate matrix)
                start_idx = 0
                for i, line in enumerate(lines):
                    if 'cm q' in line or 'cm' in line and 'q' in line:
                        start_idx = i + 1
                        break
                # Also need to find the end - before Q Q (graphics state restore)
                end_idx = len(lines)
                for i in range(len(lines) - 1, start_idx, -1):
                    line = lines[i].strip()
                    if line == 'Q Q' or line == 'Q':
                        end_idx = i
                        break
                print_drawing_commands = '\n'.join(lines[start_idx:end_idx]).strip()
            
            # Cut page: same for cut - skip initial setup
            cut_full_match = re.search(r'%%EndPageSetup\s*\n(.*?)%%Trailer', cut_content, re.DOTALL)
            if not cut_full_match:
                print("Warning: Could not extract cut drawing commands", file=sys.stderr)
                cut_drawing_commands = ""
            else:
                cut_full = cut_full_match.group(1)
                lines = cut_full.split('\n')
                # Skip lines until we pass the initial 'cm q' (coordinate matrix)
                start_idx = 0
                for i, line in enumerate(lines):
                    if 'cm q' in line or 'cm' in line and 'q' in line:
                        start_idx = i + 1
                        break
                # Also need to find the end - before Q Q and showpage
                end_idx = len(lines)
                for i in range(len(lines) - 1, start_idx, -1):
                    line = lines[i].strip()
                    if line in ('Q Q', 'Q', 'showpage'):
                        end_idx = i
                    elif line and line not in ('Q Q', 'Q', 'showpage'):
                        # Found last real drawing command
                        break
                cut_drawing_commands = '\n'.join(lines[start_idx:end_idx]).strip()
            
            # Get page header from cut file (includes setup with proper clipping for full bbox)
            page_header_match = re.search(r'(%%Page:.*?%%EndPageSetup)', cut_content, re.DOTALL)
            if not page_header_match:
                print("Error: Could not extract page header", file=sys.stderr)
                return False
            page_header = page_header_match.group(1)
            
            # Get the initial graphics state setup from cut file (has correct bbox clipping)
            cut_setup_match = re.search(r'%%EndPageSetup\s*\n(.*?cm q)', cut_content, re.DOTALL)
            if not cut_setup_match:
                print("Warning: Could not extract graphics setup", file=sys.stderr)
                graphics_setup = ""
            else:
                graphics_setup = cut_setup_match.group(1).strip()
            
            # IMPORTANT: Use CUT file as base because it has CutContour definitions in prolog
            # The print file doesn't have the spot color definitions we need
            page_start = cut_content.find('%%Page:')
            trailer_start = cut_content.find('%%Trailer')
            
            if page_start == -1 or trailer_start == -1:
                print("Error: Could not find page markers in EPS", file=sys.stderr)
                return False
            
            # Build merged content:
            # 1. Header and prolog from CUT file (has CutContour definitions)
            # 2. Single page header
            # 3. Graphics state setup (clipping and transform from CUT - uses full bbox)
            # 4. Print drawing commands (drawn first, bottom layer)
            # 5. Cut drawing commands (drawn on top)
            # 6. Single showpage
            # 7. Trailer
            merged_content = (
                cut_content[:page_start] +    # Header and prolog from CUT file (has CutContour!)
                page_header + '\n' +          # Single page header with setup
                graphics_setup + '\n' +       # Graphics state setup (clip + transform for full bbox)
                print_drawing_commands + '\n' + # Print drawing commands (bottom layer)
                cut_drawing_commands + '\n' + # Cut drawing commands (top layer)
                'Q Q\n' +                     # Close graphics state (restore)
                'showpage\n' +                # Single showpage command
                cut_content[trailer_start:]   # Trailer and EOF
            )
            
            # Write merged file
            with open(output_path, 'w', encoding='latin-1') as f:
                f.write(merged_content)
            
            print(f"Successfully merged print and cut layers: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error merging EPS files: {e}", file=sys.stderr)
            return False
    
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
        
        # Handle SVG input with cut/print layer separation
        if self.is_svg_input and self.has_cut_layer and not self.convert_everything:
            print("Processing with separate cut and print layers...")
            
            # Create temporary files for separated SVGs
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                
                cut_svg = tmpdir_path / f"{self.original_input_file.stem}_cut.svg"
                print_svg = tmpdir_path / f"{self.original_input_file.stem}_print.svg"
                
                self.cut_eps = tmpdir_path / f"{self.original_input_file.stem}_cut.eps"
                self.print_eps = tmpdir_path / f"{self.original_input_file.stem}_print.eps"
                
                # Create separated SVG files
                print("  [1/6] Separating cut and print layers...")
                if not create_svg_with_only_cut_group(self.original_input_file, cut_svg):
                    print("Error: Failed to create cut-only SVG", file=sys.stderr)
                    return False
                
                if not create_svg_without_cut_group(self.original_input_file, print_svg):
                    print("Error: Failed to create print-only SVG", file=sys.stderr)
                    return False
                
                # Convert both to EPS
                print("  [2/6] Converting cut layer to EPS...")
                if not convert_svg_to_eps(cut_svg, self.cut_eps):
                    return False
                
                print("  [3/6] Converting print layer to EPS...")
                if not convert_svg_to_eps(print_svg, self.print_eps):
                    return False
                
                # Process cut EPS with CutContour
                print("  [4/6] Applying CutContour to cut layer...")
                self.input_file = self.cut_eps
                cut_content = self.read_file()
                
                if not cut_content.startswith('%!PS-Adobe'):
                    print("Error: Cut EPS is not valid", file=sys.stderr)
                    return False
                
                cut_content = self.add_header_definitions(cut_content)
                cut_content = self.add_spot_color_support(cut_content)
                cut_content = self.replace_stroke_commands(cut_content)
                
                # Write processed cut file
                cut_processed = tmpdir_path / f"{self.original_input_file.stem}_cut_processed.eps"
                with open(cut_processed, 'w', encoding='latin-1') as f:
                    f.write(cut_content)
                
                # Merge print and processed cut files
                print("  [5/6] Merging print and cut layers...")
                if not self.merge_eps_files(self.print_eps, cut_processed, self.output_file):
                    return False
                
                # Validate with Ghostscript
                print("  [6/6] Validating output with Ghostscript...")
                validate_eps_with_gs(self.output_file)
                
                print("\nConversion complete!")
                print("The output file contains print content and CutContour cut paths")
                print(f"CutContour uses {self.CUTCONTOUR_CMYK[1]}% Magenta with {self.stroke_width} pt stroke width")
                
                return True
        
        # Handle SVG input conversion (simple mode or convert-everything mode)
        elif self.is_svg_input:
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
        
        # Validate with Ghostscript
        print("Validating output with Ghostscript...")
        validate_eps_with_gs(self.output_file)
        
        print("\nConversion complete!")
        print(f"The output file uses CutContour spot color ({self.CUTCONTOUR_CMYK[1]}% Magenta)")
        print(f"with hairline stroke width ({self.stroke_width} pt)")
        
        # Clean up intermediate EPS file if it was created from SVG
        if self.is_svg_input and self.intermediate_eps and self.intermediate_eps.exists():
            try:
                # self.intermediate_eps.unlink()
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
  %(prog)s input.svg --convert-everything-to-cut-path

SVG files are automatically detected and converted to EPS using Inkscape.

Cut/Print Layer Separation:
  If your SVG contains a group/layer with 'cut' in its name (case-insensitive),
  only that layer will be converted to CutContour paths. Other elements will
  remain as normal print paths. Use --convert-everything-to-cut-path to disable
  this behavior and convert all paths to cut paths.

The CutContour spot color (100%% Magenta) will be applied to cut paths.
"""
    )
    
    parser.add_argument('input', help='Input SVG or EPS file (SVG files converted automatically using Inkscape)')
    parser.add_argument('-o', '--output', help='Output EPS file (default: input_versaworks.eps)')
    parser.add_argument('-w', '--stroke-width', type=float, 
                        help='Stroke width in points (default: 0.25)')
    parser.add_argument('--convert-everything-to-cut-path', action='store_true',
                        help='Convert all paths to cut paths, ignoring cut/print layer separation')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0.0')
    
    args = parser.parse_args()
    
    # Create and run converter
    converter = EPSToVersaworksConverter(
        args.input, 
        args.output, 
        args.stroke_width,
        args.convert_everything_to_cut_path
    )
    success = converter.convert()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
