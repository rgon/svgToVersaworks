This program shall convert from exported Inkscape EPS files to some understood by the Versaworks printer plotter software, in order to be able to select the path and mark it as cut, paths compatible with the Roland Versaworks software.

The issue with the inkscape EPS export is that it does not export spot colors, and the cut contour line is supposed to be a spot color.

Create a python program that takes in an inkscape-exported EPS file, and modifies it so that the cut contour line is recognized as a spot color called CutContour.
To do so, it must search for any stroke color and substitute it. In the future, we may use a specific color to mark the cut contour line, but for now, we will assume that any stroke is a cut contour line.

# Specification:
the line color has to be called CutContour not black yellow and so on. 
it has to be a 'spot color' in the PDF/EPS sense
Roland Versaworks uses a spot color called CutContour, which is 100% Magenta (CMYK= 0,100,0,0).

This color is applied to a stroke with a "hairline" stroke width. The cutter recognizes this as the cut line.

From the official Roland documentation:
+ Draw a line around your image. Make sure that the start and end points of the line meet (so that the line is closed). Set the line weight (thickness):
    + CorelDRAW: hairline
    + Illustrator: 0.25 point
+ Create a new spot colour, and call it: CutContour 
+ Select the line around your image and give it the colour you have just created

If you print your sticker using VersaWorks, the software will recognise this line as a contour cutting line that should be lightly cut out. Indeed, all lines in this colour will be cut.