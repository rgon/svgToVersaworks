# Visual Workflow: Cut and Print Layer Processing

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INPUT: design.svg                                │
│                                                                           │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────┐  │
│  │  Print Layer (id="artwork")     │  │  Cut Layer (id="cut")       │  │
│  │  ┌──────────────┐               │  │  ┌──────────────┐           │  │
│  │  │  Red Fill    │               │  │  │  Outline     │           │  │
│  │  │  ████████    │               │  │  │  ┌────────┐  │           │  │
│  │  │  ████████    │               │  │  │  │        │  │           │  │
│  │  │     Text     │               │  │  │  │        │  │           │  │
│  │  └──────────────┘               │  │  │  └────────┘  │           │  │
│  │  Colors, fills, text            │  │  │  Stroke only │           │  │
│  └─────────────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
                    ┌───────────────────────────┐
                    │  Cut Layer Detection      │
                    │  (case-insensitive)       │
                    │  find_cut_group_in_svg()  │
                    └───────────────────────────┘
                                    ↓
                    ┌───────────────────────────┐
                    │  Layer Separation         │
                    │  XML manipulation         │
                    └───────────────────────────┘
                       ↓                    ↓
        ┌──────────────────────┐  ┌──────────────────────┐
        │  cut_only.svg        │  │  print_only.svg      │
        │                      │  │                      │
        │  ┌──────────────┐    │  │  ┌──────────────┐   │
        │  │  Outline     │    │  │  │  Red Fill    │   │
        │  │  ┌────────┐  │    │  │  │  ████████    │   │
        │  │  │        │  │    │  │  │  ████████    │   │
        │  │  │        │  │    │  │  │     Text     │   │
        │  │  └────────┘  │    │  │  └──────────────┘   │
        │  └──────────────┘    │  │                      │
        └──────────────────────┘  └──────────────────────┘
                  ↓                           ↓
        ┌──────────────────────┐  ┌──────────────────────┐
        │  Inkscape Export     │  │  Inkscape Export     │
        │  --export-text-to-   │  │  --export-text-to-   │
        │   path               │  │   path               │
        │  --export-ps-level=3 │  │  --export-ps-level=3 │
        └──────────────────────┘  └──────────────────────┘
                  ↓                           ↓
        ┌──────────────────────┐  ┌──────────────────────┐
        │  cut.eps             │  │  print.eps           │
        │  (intermediate)      │  │  (intermediate)      │
        └──────────────────────┘  └──────────────────────┘
                  ↓                           ↓
        ┌──────────────────────┐              │
        │  CutContour          │              │
        │  Processing          │              │
        │  ─────────────────   │              │
        │  • Add spot color    │              │
        │    definitions       │              │
        │  • Replace stroke    │              │
        │    commands          │              │
        │  • Set hairline      │              │
        │    width (0.25 pt)   │              │
        └──────────────────────┘              │
                  ↓                           ↓
        ┌──────────────────────┐  ┌──────────────────────┐
        │  cut_processed.eps   │  │  print.eps           │
        │                      │  │                      │
        │  CutContour paths    │  │  Original colors     │
        │  100% Magenta        │  │  Fills and text      │
        └──────────────────────┘  └──────────────────────┘
                       ↓                    ↓
                    ┌───────────────────────────┐
                    │  EPS Merging              │
                    │  merge_eps_files()        │
                    │  ───────────────────      │
                    │  • Extract headers        │
                    │  • Combine page content   │
                    │  • Maintain alignment     │
                    └───────────────────────────┘
                                    ↓
                    ┌───────────────────────────┐
                    │  Ghostscript Validation   │
                    │  validate_eps_with_gs()   │
                    │  ───────────────────      │
                    │  gs -dNOPAUSE -dBATCH     │
                    │     -sDEVICE=nullpage     │
                    └───────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────────┐
│                   OUTPUT: design_versaworks.eps                        │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  PostScript Header with CutContour Definitions                   │  │
│  │  %%DocumentCustomColors: (CutContour)                            │  │
│  │  %%CMYKCustomColor: 0.00 1.00 0.00 0.00 (CutContour)             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Prolog with Spot Color Operators                                │  │
│  │  /SetCutContourStroke { ... }                                    │  │
│  │  /SetHairlineStroke { ... }                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Page Content (layered)                                          │  │
│  │  ┌────────────────────────────────────────┐                      │  │
│  │  │  Print Layer (bottom)                  │                      │  │
│  │  │  ┌──────────────┐                      │                      │  │
│  │  │  │  Red Fill    │  Original colors     │                      │  │
│  │  │  │  ████████    │  Preserved as-is     │                      │  │
│  │  │  │  ████████    │                      │                      │  │
│  │  │  │     Text     │                      │                      │  │
│  │  │  └──────────────┘                      │                      │  │
│  │  └────────────────────────────────────────┘                      │  │
│  │  ┌────────────────────────────────────────┐                      │  │
│  │  │  Cut Layer (top)                       │                      │  │
│  │  │  ┌──────────────┐                      │                      │  │
│  │  │  │  CutContour  │  100% Magenta        │                      │  │
│  │  │  │  ┌────────┐  │  Hairline (0.25 pt)  │                      │  │
│  │  │  │  │        │  │  Spot color          │                      │  │
│  │  │  │  │        │  │                      │                      │  │
│  │  │  │  └────────┘  │                      │                      │  │
│  │  │  └──────────────┘                      │                      │  │
│  │  └────────────────────────────────────────┘                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  Result: Print + Cut with perfect alignment                            │
└────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      Roland Versaworks RIP                              │
│                                                                         │
│  ✓ Detects CutContour spot color (100% Magenta)                         │
│  ✓ Separates cut paths from print content                               │
│  ✓ Generates separate cut and print jobs                                │
│  ✓ Maintains alignment between print and cut                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Legend

| Symbol | Meaning |
|--------|---------|
| ████ | Fill color (print) |
| ┌──┐ | Stroke outline (cut) |
| → | Process flow |
| ✓ | Success/Complete |

## Key Points

1. **Input**: Single SVG with cut and print layers
2. **Detection**: Automatic identification of cut layer
3. **Separation**: Two temporary SVGs created
4. **Conversion**: Inkscape exports both to EPS
5. **Processing**: CutContour applied only to cut layer
6. **Merging**: Combined with maintained alignment
7. **Validation**: Ghostscript checks syntax
8. **Output**: Single EPS ready for Versaworks

## Color Handling

```
Print Layer:
  Input:  RGB/CMYK/Fill colors
  Output: Preserved exactly as designed
  
Cut Layer:
  Input:  Any stroke color
  Output: CutContour spot color (0, 100, 0, 0) CMYK
          Hairline width (0.25 pt)
```

## Alignment Guarantee

```
Both SVGs share:
  • Same canvas dimensions
  • Same viewBox
  • Same coordinate system
  • No additional transforms

Result:
  → Perfect pixel-perfect alignment
  → No registration issues
  → Cut exactly where designed
```
