# EPS to Versaworks Converter

This program converts Inkscape-exported SVG or EPS files to a Roland Versaworks compatible format. It ensures that cutting operations are properly detected.

## The problem

When exporting EPS files from Inkscape, the software does not export spot colors. However, Roland Versaworks requires cut contour lines to be defined as a specific spot color called "CutContour" with CMYK values of 0,100,0,0 (100% Magenta). Thus, it's impossible to define custom cut operations. 

### Solution
This Python program:
1. Adds the required spot color definitions to the EPS header
2. Adds PostScript functions for spot color support
3. Converts all stroke colors (RGB, CMYK, or grayscale) to the CutContour spot color
4. Sets stroke width to hairline (0.25 points) as required by Roland specifications

## Usage

### Basic Usage
```bash
python epsVersaworksConversion.py input_file.eps [output_file.eps]
```

### Examples

Convert a file with automatic output naming:
```bash
python epsVersaworksConversion.py mydesign.eps
# Creates: mydesign_versaworks.eps
```

Convert a file with custom output name:
```bash
python epsVersaworksConversion.py mydesign.eps mydesign_cutcontour.eps
```

Make executable and run directly:
```bash
chmod +x epsVersaworksConversion.py
./epsVersaworksConversion.py mydesign.eps
```

## Requirements

- Python 3.6 or higher
- No additional dependencies required (uses only standard library)

## Technical Details

### CutContour Spot Color Specification
- **Name**: CutContour
- **CMYK Values**: 0, 100, 0, 0 (100% Magenta)
- **Stroke Width**: 0.25 points (hairline)

### What the Program Does

1. **Header Modifications**:
   - Adds `%%DocumentCustomColors: (CutContour)`
   - Adds `%%CMYKCustomColor: 0 1.0 0 0 (CutContour)`

2. **PostScript Function Additions**:
   - Adds `findcmykcustomcolor` function for spot color support
   - Adds `setcustomcolor` function for applying spot colors
   - Defines the CutContour spot color variable

3. **Color Conversion**:
   - Converts RGB colors (e.g., `0.5 0.5 0.5 rg`) to `1.0 CutContour setcustomcolor`
   - Converts CMYK colors (e.g., `0.5 0.5 0.5 0.5 k`) to `1.0 CutContour setcustomcolor`
   - Converts grayscale colors (e.g., `0.5 g`) to `1.0 CutContour setcustomcolor`

4. **Stroke Width Adjustment**:
   - Adds `0.25 w` before stroke commands to set hairline width

## Testing

Run the included test script to verify functionality:
```bash
python test_conversion.py
```

## Compatibility

This program is designed to work with:
- **Input**: EPS files exported from Inkscape
- **Output**: EPS files compatible with Roland Versaworks software
- **Tested with**: Roland Versaworks RIP software

## File Structure

```
├── epsVersaworksConversion.py    # Main conversion program
├── test_conversion.py            # Test script
├── SPEC.md                       # Detailed specification
├── README.md                     # This documentation
├── *.eps                         # Sample EPS files
```

## Example Before/After

### Before (Inkscape Export)
```postscript
0.690196 0 0.690196 rg  % RGB color
1.984252 w              % Line width
% ... path commands ...
S                       % Stroke
```

### After (Versaworks Compatible)
```postscript
%%DocumentCustomColors: (CutContour)
%%CMYKCustomColor: 0 1.0 0 0 (CutContour)

% ... spot color functions ...
/CutContour 0 1.0 0 0 (CutContour) findcmykcustomcolor def

1.0 CutContour setcustomcolor  % Spot color
% ... path commands ...
0.25 w S                       % Hairline stroke
```

## Troubleshooting

### Common Issues

1. **"File not found" error**: Ensure the input EPS file exists and the path is correct
2. **Permission denied**: Make sure you have write permissions in the output directory
3. **No changes visible**: Verify that the original file contains stroke operations

### Verification

To verify the conversion worked:
1. Check that the output file contains `%%DocumentCustomColors: (CutContour)`
2. Look for `1.0 CutContour setcustomcolor` in place of original color commands
3. Confirm stroke commands now include `0.25 w`

## Contributing

This program addresses the specific need of converting Inkscape EPS exports for Roland Versaworks compatibility. If you encounter issues with other EPS sources or need additional features, please review the code and adapt as needed.

## License

This program is provided as-is for educational and practical use in converting EPS files for Roland Versaworks compatibility.