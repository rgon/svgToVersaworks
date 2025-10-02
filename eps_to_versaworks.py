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
from pathlib import Path


class EPSToVersaworksConverter:
    """Converter for EPS files to Versaworks-compatible format."""
    
    # CutContour spot color: 100% Magenta in CMYK
    CUTCONTOUR_CMYK = (0, 100, 0, 0)  # C, M, Y, K as percentages
    
    # Hairline stroke width (0.25 points = Illustrator hairline)
    HAIRLINE_WIDTH = 0.25
    
    def __init__(self, input_file, output_file=None, stroke_width=None):
        """Initialize converter with input/output files."""
        self.input_file = Path(input_file)
        
        if output_file:
            self.output_file = Path(output_file)
        else:
            stem = self.input_file.stem
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
        print(f"Converting: {self.input_file}")
        print(f"Output: {self.output_file}")
        
        # Read input
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
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert Inkscape EPS to Versaworks-compatible format with CutContour spot color',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.eps
  %(prog)s input.eps -o output_cutcontour.eps
  %(prog)s input.eps --stroke-width 0.5

The CutContour spot color (100%% Magenta) will be applied to all strokes.
"""
    )
    
    parser.add_argument('input', help='Input EPS file from Inkscape')
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
