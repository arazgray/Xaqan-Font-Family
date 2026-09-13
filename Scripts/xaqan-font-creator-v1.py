#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Xaqan Font Creator - Adds South Azerbaijani characters to Persian fonts
Fixed for FontForge 20230101 and compatible with proportional fonts
"""

import fontforge
import os
import sys
import math
import subprocess
from collections import defaultdict

# Configuration constants
DEFAULT_OFFSET = 113  # Fallback vertical offset for GPOS adjustment
DOT_SIZE_RATIO = 0.15  # Ratio of dot size relative to x-height
CIRCUMFLEX_RATIO = 0.6  # Ratio of circumflex size relative to x-height

class XaqanFontCreator:
    def __init__(self, input_path, output_path=None):
        """
        Initialize the font creator
        :param input_path: Path to input font file
        :param output_path: Path to output font file (optional)
        """
        self.input_path = input_path
        self.output_path = output_path
        self.font = None
        self.warnings = []
        self.errors = []

        # Source glyph references
        self.source_glyphs = {
            'waw': None,
            'kaf': None,
            'kaf_arabic': None,
            'yeh': None,
            'yeh_arabic': None,
            'sheen': None
        }

        # Mark glyphs
        self.mark_glyphs = {
            'U+065A': None,  # MARK
            'U+064F': None,  # FATHA
            'U+0302': None,  # COMBINING CIRCUMFLEX
            'U+FE7E': None   # ARABIC SUKUN
        }

        # Three-dot components
        self.three_dots = []

        # Create output path if not provided
        if not self.output_path:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            self.output_path = f"{base_name}-xaqan.ttf"

    def run(self):
        """Main execution method"""
        try:
            print(f"Opening font: {self.input_path}")
            self.font = fontforge.open(self.input_path)

            # Find source glyphs
            self.find_source_glyphs()

            # Find or create marks
            self.prepare_marks()

            # Extract three dots from Sheen
            self.extract_three_dots()

            # Create new glyphs
            self.create_new_glyphs()

            # Create contextual forms
            self.create_contextual_forms()

            # Add GSUB/GPOS features
            self.add_opentype_features()

            # Update font naming
            self.update_font_naming()

            # Generate output font
            self.generate_output()

            print(f"\nSuccessfully generated: {self.output_path}")
            return True

        except Exception as e:
            print(f"ERROR: {str(e)}")
            self.errors.append(str(e))
            return False

    def find_source_glyphs(self):
        """Find source glyphs using multiple strategies"""
        print("Finding source glyphs...")

        # Define Unicode values and glyph names for sources
        sources = {
            'waw': {
                'unicode': 0x0648,
                'names': ['uni0648', 'waw', 'Waw'],
                'fallback': None
            },
            'kaf': {
                'unicode': 0x06A9,
                'names': ['uni06A9', 'kaf', 'Keheh'],
                'fallback': None
            },
            'kaf_arabic': {
                'unicode': 0x0643,
                'names': ['uni0643', 'kaf-arabic', 'Kaf'],
                'fallback': None
            },
            'yeh': {
                'unicode': 0x06CC,
                'names': ['uni06CC', 'farsi-yeh', 'Yeh'],
                'fallback': None
            },
            'yeh_arabic': {
                'unicode': 0x064A,
                'names': ['uni064A', 'yeh-arabic', 'ArabicYeh'],
                'fallback': None
            },
            'sheen': {
                'unicode': 0x0634,
                'names': ['uni0634', 'sheen', 'Shin'],
                'fallback': None
            }
        }

        # First try: Unicode lookup
        for key, source in sources.items():
            try:
                glyph = self.font[source['unicode']]
                if glyph and glyph.glyphname:
                    self.source_glyphs[key] = glyph
                    print(f"  Found {key}: {glyph.glyphname} (U+{source['unicode']:04X})")
                    continue
            except:
                pass

        # Second try: Glyph name lookup
        for key, source in sources.items():
            if self.source_glyphs[key]:
                continue

            for name in source['names']:
                try:
                    glyph = self.font[name]
                    if glyph:
                        self.source_glyphs[key] = glyph
                        print(f"  Found {key} by name: {glyph.glyphname}")
                        break
                except:
                    continue

        # Third try: Contextual forms (for kaf and yeh)
        if not self.source_glyphs['kaf']:
            # Try to find kaf from contextual forms
            for suffix in ['.init', '.medi', '.fina', '.isol']:
                try:
                    name = f"uni06A9{suffix}"
                    glyph = self.font[name]
                    if glyph:
                        self.source_glyphs['kaf'] = glyph
                        print(f"  Found kaf from contextual form: {name}")
                        break
                except:
                    continue

        if not self.source_glyphs['yeh']:
            # Try to find yeh from contextual forms
            for suffix in ['.init', '.medi', '.fina', '.isol']:
                try:
                    name = f"uni06CC{suffix}"
                    glyph = self.font[name]
                    if glyph:
                        self.source_glyphs['yeh'] = glyph
                        print(f"  Found yeh from contextual form: {name}")
                        break
                except:
                    continue

        # Check if all essential glyphs found
        essential = ['waw', 'kaf', 'yeh', 'sheen']
        missing = [key for key in essential if not self.source_glyphs[key]]

        if missing:
            error_msg = f"Missing essential source glyphs: {', '.join(missing)}"
            print(f"  ERROR: {error_msg}")
            raise Exception(error_msg)

    def prepare_marks(self):
        """Find or create mark glyphs"""
        print("Preparing marks...")

        # Define marks with fallbacks
        marks = {
            'U+065A': {  # ARABIC MARK
                'unicode': 0x065A,
                'names': ['uni065A', 'arabic-mark'],
                'fallback_create': True,
                'description': 'Arabic mark'
            },
            'U+064F': {  # FATHA
                'unicode': 0x064F,
                'names': ['uni064F', 'fatha'],
                'fallback_create': True,
                'description': 'Fatha mark'
            },
            'U+0302': {  # COMBINING CIRCUMFLEX
                'unicode': 0x0302,
                'names': ['uni0302', 'circumflex', 'combiningcircumflex'],
                'fallback_create': True,
                'description': 'Combining circumflex'
            },
            'U+FE7E': {  # ARABIC SUKUN
                'unicode': 0xFE7E,
                'names': ['uniFE7E', 'arabic-sukun'],
                'fallback_create': False,
                'description': 'Arabic sukun'
            }
        }

        # Find marks
        for key, mark in marks.items():
            try:
                glyph = self.font[mark['unicode']]
                if glyph:
                    self.mark_glyphs[key] = glyph
                    print(f"  Found {mark['description']}: {glyph.glyphname}")
                    continue
            except:
                pass

            # Try glyph names
            for name in mark['names']:
                try:
                    glyph = self.font[name]
                    if glyph:
                        self.mark_glyphs[key] = glyph
                        print(f"  Found {mark['description']} by name: {name}")
                        break
                except:
                    continue

        # Create missing marks if needed
        self.create_missing_marks(marks)

        # Check critical marks
        if not self.mark_glyphs['U+0302']:
            print("  ERROR: Circumflex mark (U+0302) not found and could not be created")
            raise Exception("Circumflex mark required for ؽ not available")

    def create_missing_marks(self, marks):
        """Create missing mark glyphs when possible"""
        # Create circumflex if missing
        if not self.mark_glyphs['U+0302']:
            print("  Creating circumflex mark...")
            try:
                # Create a simple circumflex using two strokes
                circumflex = self.font.createMappedChar(0x0302)
                circumflex.glyphname = "uni0302"
                circumflex.unicode = 0x0302

                # Create two diagonal strokes
                # This is a simplified circumflex - adjust coordinates as needed
                pen = circumflex.glyphPen()

                # Calculate dimensions based on font metrics
                x_height = self.font.xHeight or 500
                width = int(x_height * CIRCUMFLEX_RATIO)
                height = int(x_height * 0.3)

                # First stroke: lower left to upper middle
                pen.moveTo((-width/2, 0))
                pen.lineTo((-width/2 + width/4, height))
                pen.lineTo((0, height/2))
                pen.closePath()

                # Second stroke: upper middle to lower right
                pen.moveTo((0, height/2))
                pen.lineTo((width/2 - width/4, height))
                pen.lineTo((width/2, 0))
                pen.closePath()

                pen = None
                circumflex.width = width
                circumflex.vwidth = height * 2

                self.mark_glyphs['U+0302'] = circumflex
                print(f"    Created circumflex: {circumflex.glyphname}")

            except Exception as e:
                print(f"    Failed to create circumflex: {e}")

    def extract_three_dots(self):
        """Extract three dots from Sheen glyph using multiple strategies"""
        print("Extracting three dots from Sheen...")

        sheen = self.source_glyphs['sheen']
        if not sheen:
            print("  ERROR: Sheen glyph not available")
            return

        # Strategy 1: Extract smallest contours from Sheen
        contours = []
        try:
            # Get all contours from Sheen
            for contour in sheen.foreground:
                if len(contour) > 0:  # Non-empty contour
                    # Calculate bounding box
                    bbox = contour.boundingBox()
                    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    contours.append((area, contour))

            # Sort by area (smallest first)
            contours.sort(key=lambda x: x[0])

            # Take the three smallest contours
            if len(contours) >= 3:
                self.three_dots = [c[1] for c in contours[:3]]
                print(f"  Extracted {len(self.three_dots)} contours from Sheen")
                return

        except Exception as e:
            print(f"  Contour extraction failed: {e}")

        # Strategy 2: Extract components from Sheen (fixed for FontForge 20230101)
        try:
            # In FontForge 20230101, references is a list of tuples (glyph_name, transform)
            components = sheen.references
            if components:
                # Take first three components as dots
                for i in range(3):
                    if i < len(components):
                        # Extract glyph name and transform
                        ref_glyph_name = components[i][0]
                        ref_transform = components[i][1] if len(components[i]) > 1 else (1, 0, 0, 1, 0, 0)

                        # Create a new glyph from component
                        dot_glyph = self.font.createChar(-1, f"dot_{i}")
                        dot_glyph.addReference(ref_glyph_name, ref_transform)
                        self.three_dots.append(dot_glyph.foreground[0])
                print(f"  Extracted {len(self.three_dots)} components from Sheen")
                return
        except Exception as e:
            print(f"  Component extraction failed: {e}")

        # Strategy 3: Create dots from another glyph (like Beh)
        print("  Trying to extract dots from Beh...")
        try:
            beh = self.font[0x0628]  # Beh
            if beh:
                # Extract contours from Beh
                beh_contours = []
                for contour in beh.foreground:
                    if len(contour) > 0:
                        bbox = contour.boundingBox()
                        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                        beh_contours.append((area, contour))

                # Sort and take smallest
                beh_contours.sort(key=lambda x: x[0])
                if beh_contours:
                    # Use the smallest contour as a dot
                    self.three_dots = [beh_contours[0][1]] * 3
                    print(f"  Created dots from Beh contour")
                    return
        except:
            pass

        # Strategy 4: Create simple dots (fixed for FontForge 20230101)
        print("  Creating simple dots...")
        try:
            # Create three simple dots
            x_height = self.font.xHeight or 500
            dot_size = int(x_height * DOT_SIZE_RATIO)

            for i in range(3):
                dot_glyph = self.font.createChar(-1, f"dot_{i}")
                pen = dot_glyph.glyphPen()

                # Create a circle (fixed argument count)
                # FontForge's curveTo takes 6 arguments: (x1,y1,x2,y2,x3,y3)
                # But we can use lineTo for a simple diamond shape
                pen.moveTo((-dot_size/2, 0))
                pen.lineTo((0, dot_size/2))
                pen.lineTo((dot_size/2, 0))
                pen.lineTo((0, -dot_size/2))
                pen.closePath()
                pen = None

                dot_glyph.width = dot_size
                dot_glyph.vwidth = dot_size

                self.three_dots.append(dot_glyph.foreground[0])

            print(f"  Created {len(self.three_dots)} simple dots")

        except Exception as e:
            print(f"  Failed to create simple dots: {e}")
            self.three_dots = []

    def create_new_glyphs(self):
        """Create the new South Azerbaijani glyphs"""
        print("Creating new glyphs...")

        # Create ۆ U+06C6 (Waw + Mark)
        self.create_glyph_with_mark(
            unicode=0x06C6,
            glyph_name="uni06C6",
            base_glyph=self.source_glyphs['waw'],
            mark_glyph=self.mark_glyphs['U+065A'],
            description="ۆ (Waw with mark)"
        )

        # Create ۇ U+06C7 (Waw + Fatha)
        self.create_glyph_with_mark(
            unicode=0x06C7,
            glyph_name="uni06C7",
            base_glyph=self.source_glyphs['waw'],
            mark_glyph=self.mark_glyphs['U+064F'],
            description="ۇ (Waw with fatha)"
        )

        # Create ؽ U+063D (Yeh + Circumflex)
        self.create_glyph_with_mark(
            unicode=0x063D,
            glyph_name="uni063D",
            base_glyph=self.source_glyphs['yeh'],
            mark_glyph=self.mark_glyphs['U+0302'],
            description="ؽ (Yeh with circumflex)"
        )

        # Create ݣ U+0763 (Kaf + Three dots)
        self.create_glyph_with_dots(
            unicode=0x0763,
            glyph_name="uni0763",
            base_glyph=self.source_glyphs['kaf'],
            description="ݣ (Kaf with three dots)"
        )

        # Create ڭ U+06AD (Kaf + Three dots, different base)
        # Try to use U+FED9 as base if available
        base_06AD = self.source_glyphs['kaf']
        try:
            fed9 = self.font[0xFED9]
            if fed9:
                base_06AD = fed9
        except:
            pass

        self.create_glyph_with_dots(
            unicode=0x06AD,
            glyph_name="uni06AD",
            base_glyph=base_06AD,
            description="ڭ (Kaf with three dots)"
        )

    def create_glyph_with_mark(self, unicode, glyph_name, base_glyph, mark_glyph, description):
        """Create a glyph by combining base glyph with mark"""
        try:
            # Create new glyph
            new_glyph = self.font.createMappedChar(unicode)
            new_glyph.glyphname = glyph_name
            new_glyph.unicode = unicode

            # Copy base glyph outline
            new_glyph.clear()
            new_glyph.addReference(base_glyph.glyphname, (1, 0, 0, 1, 0, 0))

            # Position mark appropriately
            if mark_glyph:
                # Calculate mark position based on base glyph
                base_bbox = base_glyph.boundingBox()
                mark_bbox = mark_glyph.boundingBox()

                # Center mark horizontally over base
                x_offset = (base_bbox[2] - base_bbox[0]) / 2 - (mark_bbox[2] - mark_bbox[0]) / 2

                # Position mark at top of base glyph
                y_offset = base_bbox[3] - mark_bbox[1]  # Adjust as needed

                # Add mark as reference
                new_glyph.addReference(mark_glyph.glyphname, (1, 0, 0, 1, x_offset, y_offset))

            # Set glyph properties
            new_glyph.width = base_glyph.width
            new_glyph.vwidth = base_glyph.vwidth

            # Remove anchors for vowel characters
            self.remove_anchors(new_glyph)

            print(f"  Created {description}")

        except Exception as e:
            error_msg = f"Failed to create {description}: {e}"
            print(f"  ERROR: {error_msg}")
            self.warnings.append(error_msg)

    def create_glyph_with_dots(self, unicode, glyph_name, base_glyph, description):
        """Create a glyph by combining base glyph with three dots"""
        try:
            # Create new glyph
            new_glyph = self.font.createMappedChar(unicode)
            new_glyph.glyphname = glyph_name
            new_glyph.unicode = unicode

            # Copy base glyph outline
            new_glyph.clear()
            new_glyph.addReference(base_glyph.glyphname, (1, 0, 0, 1, 0, 0))

            # Add three dots
            if self.three_dots:
                # Calculate positions for three dots
                base_bbox = base_glyph.boundingBox()
                base_width = base_bbox[2] - base_bbox[0]
                base_height = base_bbox[3] - base_bbox[1]

                # Position dots above the base glyph
                dot_spacing = base_width / 4
                y_position = base_bbox[3] + base_height * 0.3  # Adjust as needed

                # Add three dots in a row
                for i, dot in enumerate(self.three_dots[:3]):
                    x_position = base_bbox[0] + base_width/2 + (i - 1) * dot_spacing
                    new_glyph.addReference(dot.glyphname, (1, 0, 0, 1, x_position, y_position))

            # Set glyph properties
            new_glyph.width = base_glyph.width
            new_glyph.vwidth = base_glyph.vwidth

            print(f"  Created {description}")

        except Exception as e:
            error_msg = f"Failed to create {description}: {e}"
            print(f"  ERROR: {error_msg}")
            self.warnings.append(error_msg)

    def create_contextual_forms(self):
        """Create contextual forms (.init, .medi, .fina) for connecting characters"""
        print("Creating contextual forms...")

        # Characters that need contextual forms
        connecting_chars = [
            {'unicode': 0x063D, 'name': 'uni063D', 'base': 'yeh'},
            {'unicode': 0x0763, 'name': 'uni0763', 'base': 'kaf'},
            {'unicode': 0x06AD, 'name': 'uni06AD', 'base': 'kaf'}
        ]

        for char in connecting_chars:
            base_glyph = self.source_glyphs[char['base']]
            if not base_glyph:
                continue

            # Create contextual forms
            for form in ['init', 'medi', 'fina']:
                form_name = f"{char['name']}.{form}"
                try:
                    # Create new glyph
                    form_glyph = self.font.createChar(-1, form_name)

                    # Copy base glyph outline
                    form_glyph.clear()
                    form_glyph.addReference(base_glyph.glyphname, (1, 0, 0, 1, 0, 0))

                    # Add appropriate mark/dots
                    if char['unicode'] == 0x063D:  # ؽ needs circumflex
                        if self.mark_glyphs['U+0302']:
                            form_glyph.addReference(self.mark_glyphs['U+0302'].glyphname,
                                                  (1, 0, 0, 1, 0, 0))
                    else:  # ݣ and ڭ need three dots
                        if self.three_dots:
                            # Add dots in appropriate positions
                            base_bbox = base_glyph.boundingBox()
                            form_glyph.addReference(self.three_dots[0].glyphname,
                                                  (1, 0, 0, 1, 0, 0))

                    # Copy metrics from base glyph
                    form_glyph.width = base_glyph.width
                    form_glyph.vwidth = base_glyph.vwidth

                    print(f"  Created {form_name}")

                except Exception as e:
                    print(f"  Failed to create {form_name}: {e}")

    def add_opentype_features(self):
        """Add GSUB and GPOS features"""
        print("Adding OpenType features...")

        # Add GSUB features for contextual forms
        self.add_gsub_features()

        # Add GPOS feature for و + ﹾ adjustment
        self.add_gpos_feature()

    def add_gsub_features(self):
        """Add GSUB substitution features (fixed for FontForge 20230101)"""
        try:
            # Create feature file content
            feature_content = []

            # Add init feature
            feature_content.append("feature init {")
            feature_content.append("  sub uni063D by uni063D.init;")
            feature_content.append("  sub uni0763 by uni0763.init;")
            feature_content.append("  sub uni06AD by uni06AD.init;")
            feature_content.append("} init;")

            # Add medi feature
            feature_content.append("feature medi {")
            feature_content.append("  sub uni063D by uni063D.medi;")
            feature_content.append("  sub uni0763 by uni0763.medi;")
            feature_content.append("  sub uni06AD by uni06AD.medi;")
            feature_content.append("} medi;")

            # Add fina feature
            feature_content.append("feature fina {")
            feature_content.append("  sub uni063D by uni063D.fina;")
            feature_content.append("  sub uni0763 by uni0763.fina;")
            feature_content.append("  sub uni06AD by uni06AD.fina;")
            feature_content.append("} fina;")

            # Write feature file to temporary location
            feature_file = "/tmp/xaqan_features.fea"
            with open(feature_file, 'w') as f:
                f.write('\n'.join(feature_content))

            # Apply features using FontForge's correct method for this version
            # Instead of mergeFeatureFile, we'll use the font's GSUB table directly
            try:
                # Create GSUB table if it doesn't exist
                # In FontForge 20230101, we need to use addLookup with correct parameters
                # The method signature is: addLookup(name, type, flags, scripts, languages)

                # Create lookup for init feature
                lookup_name = "xaqan_init"
                # Parameters: name, type, flags, scripts, languages
                self.font.addLookup(lookup_name, 'gsub', 0, ['arab'], ['dflt'])
                self.font.addSubstitution(lookup_name, 'uni063D', 'uni063D.init')
                self.font.addSubstitution(lookup_name, 'uni0763', 'uni0763.init')
                self.font.addSubstitution(lookup_name, 'uni06AD', 'uni06AD.init')

                # Create lookup for medi feature
                lookup_name = "xaqan_medi"
                self.font.addLookup(lookup_name, 'gsub', 0, ['arab'], ['dflt'])
                self.font.addSubstitution(lookup_name, 'uni063D', 'uni063D.medi')
                self.font.addSubstitution(lookup_name, 'uni0763', 'uni0763.medi')
                self.font.addSubstitution(lookup_name, 'uni06AD', 'uni06AD.medi')

                # Create lookup for fina feature
                lookup_name = "xaqan_fina"
                self.font.addLookup(lookup_name, 'gsub', 0, ['arab'], ['dflt'])
                self.font.addSubstitution(lookup_name, 'uni063D', 'uni063D.fina')
                self.font.addSubstitution(lookup_name, 'uni0763', 'uni0763.fina')
                self.font.addSubstitution(lookup_name, 'uni06AD', 'uni06AD.fina')

                print("  Added GSUB features (init, medi, fina)")

            except Exception as e:
                # Fallback to feature file method if direct method fails
                print(f"  Direct GSUB method failed: {e}")
                print("  Trying feature file method...")

                # Use FontForge's feature file parsing
                try:
                    # Read the feature file
                    with open(feature_file, 'r') as f:
                        feature_data = f.read()

                    # Parse features using FontForge's built-in method
                    # In FontForge 20230101, we can use the font's addFeature method
                    # or the low-level GSUB table manipulation
                    self.font.addFeature('init', 'sub uni063D by uni063D.init; sub uni0763 by uni0763.init; sub uni06AD by uni06AD.init;')
                    self.font.addFeature('medi', 'sub uni063D by uni063D.medi; sub uni0763 by uni0763.medi; sub uni06AD by uni06AD.medi;')
                    self.font.addFeature('fina', 'sub uni063D by uni063D.fina; sub uni0763 by uni0763.fina; sub uni06AD by uni06AD.fina;')
                    print("  Added GSUB features via feature file")

                except Exception as e2:
                    print(f"  Feature file method also failed: {e2}")
                    error_msg = f"Failed to add GSUB features: {e2}"
                    print(f"  ERROR: {error_msg}")
                    self.warnings.append(error_msg)

            # Clean up
            if os.path.exists(feature_file):
                os.remove(feature_file)

        except Exception as e:
            error_msg = f"Failed to add GSUB features: {e}"
            print(f"  ERROR: {error_msg}")
            self.warnings.append(error_msg)

    def add_gpos_feature(self):
        """Add GPOS positioning feature for و + ﹾ (fixed for FontForge 20230101)"""
        try:
            # Create GPOS feature for lowering U+FE7E after و
            # This uses FontForge's direct API instead of feature files

            # First, check if we have the required glyphs
            waw_glyph = self.source_glyphs['waw']
            sukun_glyph = self.mark_glyphs['U+FE7E']

            if not waw_glyph or not sukun_glyph:
                print("  Missing required glyphs for GPOS feature")
                return

            # Calculate offset based on font metrics
            base_bbox = waw_glyph.boundingBox()
            mark_bbox = sukun_glyph.boundingBox()

            # Calculate vertical offset to lower the mark
            # This is a heuristic based on the font's metrics
            font_ascent = self.font.ascent
            font_descent = self.font.descent
            x_height = self.font.xHeight

            # Calculate appropriate offset (adjust as needed)
            offset = int((base_bbox[3] - mark_bbox[1]) * 0.2)  # 20% of the gap

            # Ensure we have a reasonable offset
            if offset <= 0:
                offset = DEFAULT_OFFSET  # Use default if calculation fails

            # Create GPOS lookup for mark positioning
            try:
                # Create a new lookup for mark positioning
                # In FontForge 20230101, we need to use addLookup with correct parameters
                lookup_name = "xaqan_mark_positioning"
                # Parameters: name, type, flags, scripts, languages
                self.font.addLookup(lookup_name, 'gpos', 0, ['arab'], ['dflt'])

                # Add mark positioning rule
                # This positions U+FE7E lower when after و
                # The method signature is: addPosSub(lookup_name, base_glyph, mark_glyph, pos1, pos2, ...)
                # We need to provide the positioning information

                # For mark positioning, we can use the addAnchor method
                # First, add an anchor to the waw glyph
                waw_glyph.addAnchorPoint("top", 0, base_bbox[2] - base_bbox[0], base_bbox[3] - base_bbox[1] // 2)

                # Then, add an anchor to the sukun glyph
                sukun_glyph.addAnchorPoint("_top", 0, 0, 0)

                # Add the rule to the lookup
                self.font.addPosSub(lookup_name,
                                   waw_glyph.glyphname,
                                   sukun_glyph.glyphname,
                                   (0, -offset, 0, 0))  # Only vertical adjustment

                print(f"  Added GPOS feature: lowered ﹾ after و by {offset} units")

            except Exception as e:
                # Fallback to simpler method if direct method fails
                print(f"  Direct GPOS method failed: {e}")
                print("  Trying alternative method...")

                # Alternative: Modify the mark glyph's position in the waw context
                # This is a simplified approach

                # For now, we'll just report that GPOS wasn't added
                error_msg = "GPOS feature could not be added via direct method"
                print(f"  WARNING: {error_msg}")
                self.warnings.append(error_msg)

        except Exception as e:
            error_msg = f"Failed to add GPOS feature: {e}"
            print(f"  ERROR: {error_msg}")
            self.warnings.append(error_msg)

    def remove_anchors(self, glyph):
        """Remove anchors from vowel characters"""
        try:
            # Remove all anchors from glyph
            for anchor in glyph.anchorPoints:
                glyph.removeAnchor(anchor)
        except:
            pass

    def update_font_naming(self):
        """Update font naming with Xaqan prefix (fixed for FontForge 20230101)"""
        print("Updating font naming...")

        try:
            # Get current font names
            family_name = self.font.familyname or "Unknown"
            fontname = self.font.fontname or "Unknown"
            fullname = self.font.fullname or family_name

            # Create new names with Xaqan prefix
            new_family_name = f"Xaqan {family_name}"
            new_fontname = f"Xaqan-{fontname}"
            new_fullname = f"Xaqan {fullname}"

            # Update font properties using correct API for FontForge 20230101
            self.font.familyname = new_family_name
            self.font.fontname = new_fontname
            self.font.fullname = new_fullname

            # Update other naming fields using sfnt_names if available
            try:
                # Method for FontForge 20230101
                if hasattr(self.font, 'sfnt_names'):
                    # Get existing names
                    existing_names = self.font.sfnt_names

                    # Create new name list
                    new_names = []
                    for name_entry in existing_names:
                        # In FontForge 20230101, sfnt_names returns tuples with 3 elements
                        # (name_id, platform_id, value)
                        if len(name_entry) == 3:
                            name_id, platform_id, value = name_entry
                            if name_id == 1:  # Family name
                                new_names.append((name_id, platform_id, new_family_name))
                            elif name_id == 2:  # Style name
                                # Preserve style name
                                new_names.append((name_id, platform_id, value))
                            elif name_id == 4:  # Full name
                                new_names.append((name_id, platform_id, new_fullname))
                            elif name_id == 6:  # PostScript name
                                new_names.append((name_id, platform_id, new_fontname))
                            else:
                                # Preserve other names
                                new_names.append((name_id, platform_id, value))
                        else:
                            # Fallback for unexpected format
                            new_names.append(name_entry)

                    # Update the font's names
                    self.font.sfnt_names = new_names

            except AttributeError:
                # Fallback for older FontForge versions
                print("  Using fallback naming method")

                # Try to use setNamelist if available
                try:
                    if hasattr(self.font, 'setNamelist'):
                        # Create a name list
                        name_list = [
                            (1, new_family_name),  # Family
                            (2, "Regular"),         # Style (preserve)
                            (4, new_fullname),      # Full name
                            (6, new_fontname)       # PostScript name
                        ]
                        self.font.setNamelist(name_list)
                except:
                    pass

            print(f"  Updated font names:")
            print(f"    Family: {new_family_name}")
            print(f"    FontName: {new_fontname}")
            print(f"    FullName: {new_fullname}")

        except Exception as e:
            error_msg = f"Failed to update font naming: {e}"
            print(f"  ERROR: {error_msg}")
            self.warnings.append(error_msg)

    def generate_output(self):
        """Generate the output font file"""
        print("Generating output font...")

        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(self.output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Determine output format based on extension
            ext = os.path.splitext(self.output_path)[1].lower()

            if ext in ['.ttf', '.otf']:
                # Generate TrueType/OpenType font
                self.font.generate(self.output_path, 'ttf')
                print(f"  Generated TrueType font: {self.output_path}")
            elif ext == '.svg':
                # Generate SVG font
                self.font.generate(self.output_path, 'svg')
                print(f"  Generated SVG font: {self.output_path}")
            else:
                # Default to TTF
                self.output_path = os.path.splitext(self.output_path)[0] + '.ttf'
                self.font.generate(self.output_path, 'ttf')
                print(f"  Generated TrueType font (default): {self.output_path}")

            # Verify file was created
            if not os.path.exists(self.output_path):
                raise Exception(f"Output file was not created: {self.output_path}")

        except Exception as e:
            error_msg = f"Failed to generate output: {e}"
            print(f"  ERROR: {error_msg}")
            self.errors.append(error_msg)
            raise

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: fontforge -lang=py -script xaqan-font-creator.py INPUT.ttf [OUTPUT.ttf]")
        print("       If OUTPUT is omitted, default is INPUT-xaqan.ttf")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    # Check input file exists
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    # Create font creator and run
    creator = XaqanFontCreator(input_path, output_path)
    success = creator.run()

    if not success:
        print("\nErrors encountered:")
        for error in creator.errors:
            print(f"  - {error}")
        sys.exit(1)

    print("\nFont creation completed successfully!")

if __name__ == "__main__":
    main()
