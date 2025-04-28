# -*- coding: utf-8 -*-
import os
import sys
import random
import datetime
import math
from midiutil import MIDIFile
import traceback
import platform
import subprocess

# --- Try importing PyQt6 ---
try:
    # print("DEBUG: Importing PyQt6 modules...") # DEBUG
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QPushButton, QCheckBox, QMessageBox, QFileDialog, QFrame, QSpacerItem,
        QSizePolicy, QRadioButton, QButtonGroup, QSpinBox, QGroupBox
    )
    from PyQt6.QtGui import QFont, QPalette, QColor, QIcon, QDrag, QPixmap, QPainter, QBrush, QPen
    from PyQt6.QtCore import (
        Qt, QCoreApplication, QSize, QMimeData, QUrl, QStandardPaths, QPoint, QRectF
    )
    # print("DEBUG: PyQt6 modules imported successfully.") # DEBUG
except ImportError:
    # Handle Import Error (same as before)
    try:
        app = QApplication(sys.argv)
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setWindowTitle("Installation Error")
        error_box.setText("ERROR: PyQt6 is not installed.")
        error_box.setInformativeText("Please install it using:\npip install PyQt6")
        error_box.exec()
    except Exception as e:
        print("ERROR: PyQt6 is not installed. Please install it using:")
        print("pip install PyQt6")
        print(f"(Also encountered an error showing the message box: {e})")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error during PyQt6 import: {e}") # DEBUG
    traceback.print_exc()
    sys.exit(1)

# --- Helper function for PyInstaller resource path ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # This attribute exists when running the bundled app
        base_path = sys._MEIPASS
    except Exception:
        # sys._MEIPASS doesn't exist, so we're likely running in development
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Key and MIDI Note Data ---
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ROOT_NOTES_MIDI = {name: 60 + i for i, name in enumerate(NOTE_NAMES)}
STYLE_OPTIONS = ["Chorgi", "Jazzy"] # Blues handled by Progression Style now
MELODY_STYLE_OPTIONS = ["Legato", "Staccato"]
MELODY_SPEED_OPTIONS = ["Slow", "Medium", "Fast"]
MELODY_OCTAVE_OPTIONS = ["Mid", "High"]
# CHORD_RHYTHM_OPTIONS = ["Block", "Rhythmic"] # Removed, handled by Chord Rate
CHORD_BIAS_OPTIONS = ["Standard", "Darker", "Lighter"] # Added Lighter
CHORD_COMPLEXITY_OPTIONS = ["Standard (Triads/7ths)", "Extra (Extensions)"]
NUM_BARS_OPTIONS = ["4 Bars", "8 Bars", "12 Bars", "16 Bars", "24 Bars"]
ARP_STYLE_OPTIONS = ["Random (Consistent)", "Random (Per Bar)", "Ascending", "Descending", "Up-Down", "Random Notes", "Converge/Diverge"]
ARP_OCTAVE_OPTIONS = ["Original", "+1 Octave", "-1 Octave", "+2 Octaves", "-2 Octaves", "+3 Octaves", "-3 Octaves"]
# --- MODIFIED: Removed Jazz Licks ---
MELODY_GEN_STYLE_OPTIONS = ["Chord Tone Focus", "Scale Walker", "Experimental", "Leaps & Steps", "Minimalist", "Sustained Lead", "Random Style"]
REGENERATE_PART_OPTIONS = ["Arp", "Melody", "Bass"]
THEME_OPTIONS = ["Dark (Nord)", "Light (Grey)"] # Renamed Light theme

# --- NEW: Progression Options ---
PROG_STYLE_OPTIONS = ["Smooth Random", "Pop (I-vi-IV-V)", "Pachelbel-ish", "ii-V-I Focused", "Blues (12 Bar)"]
CHORD_RATE_OPTIONS = ["1 / Bar", "2 / Bar"]
VOICING_STYLE_OPTIONS = ["Root Position", "Allow Inversions", "Prefer Drop 2"]
CADENCE_OPTIONS = ["Any", "Authentic (V-I)", "Plagal (IV-I)"]

# --- NEW: Bass Style Options ---
BASS_STYLE_OPTIONS = ["Standard", "Walking (Jazz)", "Pop", "RnB", "Hip Hop", "808"]

# --- NEW: Melody Instrument Options ---
MELODY_INSTRUMENT_OPTIONS = ["None", "Synth Lead", "Keys", "Piano", "Pluck"]


# --- Global variables to store generated data ---
generated_chords_progression = [] # Now stores (chord_name, original_notes, midi_notes, root_note, duration_beats)
generated_arp_midi_data = [] # Stores (pitch, start_time, duration, velocity)
generated_bass_midi_data = [] # Stores (pitch, start_time, duration)
generated_melody_midi_data = [] # Stores (pitch, start_time, duration)
last_generated_key = ""
last_generated_key_type = "minor" # Default, gets updated
last_generated_num_bars = 12 # Defaulting to 12 for Blues relevance
# last_chord_rhythm_selection = "Block" # Removed
last_complexity_selection = "Standard (Triads/7ths)"
last_style_selection = "Chorgi" # Main style for pool generation
last_generated_filename_base = ""
last_saved_midi_path = None
save_directory = None
generation_count = 0


# --- Helper Functions ---
# (Helper function definitions remain the same - calculate_inversion, get_average_pitch, etc.)
def calculate_inversion(root_pos_notes, inv_num):
    """Calculates MIDI notes for a standard chord inversion."""
    if not isinstance(root_pos_notes, list): return []
    notes = sorted(list(root_pos_notes))
    num_notes = len(notes)
    if inv_num < 0 or inv_num >= num_notes: return notes
    if inv_num == 0: return notes
    notes_to_move = notes[:inv_num]
    remaining_notes = notes[inv_num:]
    moved_notes = [note + 12 for note in notes_to_move]
    inverted_notes = sorted(remaining_notes + moved_notes)
    return inverted_notes

def get_average_pitch(notes):
    """Calculates the average MIDI note number for a list of notes."""
    if not notes or not isinstance(notes, list): return 0
    numeric_notes = [n for n in notes if isinstance(n, (int, float))]
    if not numeric_notes: return 0
    return sum(numeric_notes) / len(numeric_notes)

def transpose_notes(notes, semitones):
    """Transposes a list of MIDI notes by a given number of semitones."""
    if not isinstance(notes, list): return []
    return [note + semitones for note in notes if isinstance(note, (int, float))]

def calculate_drop2_voicing(notes):
    """Calculates Drop 2 voicing."""
    if not isinstance(notes, list) or len(notes) != 4: return sorted(list(notes))
    notes_sorted = sorted(list(notes))
    note_to_drop = notes_sorted[2]
    remaining_notes = notes_sorted[:2] + notes_sorted[3:]
    voiced_notes = sorted(remaining_notes + [note_to_drop - 12])
    return voiced_notes

def calculate_spread_voicing(notes):
    """Calculates a simple spread voicing."""
    if not isinstance(notes, list) or len(notes) < 3: return sorted(list(notes))
    notes_sorted = sorted(list(notes))
    num_notes = len(notes_sorted)
    note_to_raise = notes_sorted[num_notes - 2]
    remaining_notes = notes_sorted[:num_notes - 2] + notes_sorted[num_notes - 1:]
    voiced_notes = sorted(remaining_notes + [note_to_raise + 12])
    return voiced_notes

# --- Arpeggiator Pattern Functions ---
# (Arpeggiator functions remain unchanged - get_ascending_pattern, etc.)
def get_ascending_pattern(num_notes):
    """Generates indices for an ascending pattern."""
    if num_notes <= 0: return []
    return list(range(num_notes))

def get_descending_pattern(num_notes):
    """Generates indices for a descending pattern."""
    if num_notes <= 0: return []
    return list(range(num_notes - 1, -1, -1))

def get_up_down_pattern(num_notes):
    """Generates indices for an up-then-down pattern."""
    if num_notes <= 0: return []
    up_part = list(range(num_notes))
    down_part = list(range(num_notes - 2, -1, -1))
    return up_part + down_part

def get_random_notes_pattern(num_notes):
    """Generates indices by randomly picking from available notes."""
    if num_notes <= 0: return []
    # Generate pattern length based on typical 8th/16th note usage in a bar
    pattern_len = random.choice([8, 12, 16])
    return [random.randint(0, num_notes - 1) for _ in range(pattern_len)]

def get_converge_diverge_pattern(num_notes):
    """Generates indices moving from outside in, or inside out."""
    if num_notes <= 0: return []
    indices = list(range(num_notes)); pattern = []
    use_converge = random.choice([True, False])
    if use_converge:
        low = 0; high = num_notes - 1
        while low <= high:
            pattern.append(indices[low])
            if low != high: pattern.append(indices[high])
            low += 1; high -= 1
    else: # Diverge
        mid = num_notes // 2
        if num_notes % 2 == 1: pattern.append(indices[mid]); left = mid - 1; right = mid + 1
        else: left = mid - 1; right = mid # Start from middle two for even count
        while left >= 0 and right < num_notes: # Ensure indices are valid
            pattern.append(indices[left]); pattern.append(indices[right]);
            left -= 1; right += 1
    # Repeat pattern to fill a typical rhythmic length (e.g., 8 eighth notes)
    full_pattern = []; target_len = 8
    while len(full_pattern) < target_len: full_pattern.extend(pattern)
    return full_pattern[:target_len] # Trim excess

arp_pattern_functions_map = {
    "Ascending": get_ascending_pattern, "Descending": get_descending_pattern,
    "Up-Down": get_up_down_pattern, "Random Notes": get_random_notes_pattern,
    "Converge/Diverge": get_converge_diverge_pattern
}
arp_pattern_functions_list = list(arp_pattern_functions_map.values())

# --- Helper Function to get melody rhythm patterns based on speed ---
# (get_melody_rhythm_placements remains unchanged)
def get_melody_rhythm_placements(melody_speed):
    """Returns a list of possible rhythmic placements based on speed."""
    # Each placement is a list of (start_offset_within_beat, duration_fraction_of_beat) tuples
    if melody_speed == "Slow":
        placements = [
            [(0, 1.0)], [(0, 0.5)], [(0, 2.0)], [(0, 0.75), (0.75, 0.25)],
        ]
    elif melody_speed == "Fast":
        placements = [
            [(0, 0.25)], [(0, 0.5)], [(0, 0.25), (0.25, 0.25)],
            [(0, 0.125), (0.125, 0.125)], [(0, 0.333), (0.333, 0.333)], # Approx triplet
            [(0, 0.25), (0.5, 0.25)], [(0, 0.166), (0.166, 0.166), (0.333, 0.166)], # Approx triplet feel
        ]
    else: # Medium (default)
        placements = [
            [(0, 0.5)], [(0, 1.0)], [(0, 0.5), (0.5, 0.5)],
            [(0, 0.25), (0.25, 0.25)], [(0, 0.75), (0.75, 0.25)], [(0.5, 0.5)],
        ]
    return placements if placements else [[(0, 1.0)]] # Fallback


# --- Helper Function to get Scale Notes ---
# (get_major/minor_scale_notes remains unchanged)
def get_major_scale_notes(root_midi_note):
    """Returns a list of MIDI notes for the major scale."""
    scale_intervals = [0, 2, 4, 5, 7, 9, 11]
    return [(root_midi_note + i) for i in scale_intervals]

def get_natural_minor_scale_notes(root_midi_note):
    """Returns a list of MIDI notes for the natural minor scale."""
    scale_intervals = [0, 2, 3, 5, 7, 8, 10]
    return [(root_midi_note + i) for i in scale_intervals]


# --- Chord Pool Generation ---
# Now includes 'generate_blues_chord_pool' for clarity
def generate_chorgi_major_chord_pool(key_root_name, root_midi_note, complexity="Standard (Triads/7ths)"):
    pool = {}; scale_notes = get_major_scale_notes(root_midi_note); is_extra = complexity == "Extra (Extensions)"
    # Simplified chord_defs for brevity, original file has full definitions
    chord_defs = { "I": {"name": "maj", "intervals": [0, 4, 7]}, "Imaj7": {"name": "maj7", "intervals": [0, 4, 7, 11]},
                   "ii": {"name": "m", "intervals": [0, 3, 7]}, "ii7": {"name": "m7", "intervals": [0, 3, 7, 10]},
                   "iii": {"name": "m", "intervals": [0, 3, 7]}, "iii7": {"name": "m7", "intervals": [0, 3, 7, 10]},
                   "IV": {"name": "maj", "intervals": [0, 4, 7]}, "IVmaj7": {"name": "maj7", "intervals": [0, 4, 7, 11]},
                   "V": {"name": "maj", "intervals": [0, 4, 7]}, "V7": {"name": "7", "intervals": [0, 4, 7, 10]},
                   "vi": {"name": "m", "intervals": [0, 3, 7]}, "vi7": {"name": "m7", "intervals": [0, 3, 7, 10]},
                   "vii": {"name": "dim", "intervals": [0, 3, 6]}, "viiø7": {"name": "m7b5", "intervals": [0, 3, 6, 10]},
                   # Extensions (examples)
                   "Imaj9": {"name": "maj9", "intervals": [0, 4, 7, 11, 14]}, "V9": {"name": "9", "intervals": [0, 4, 7, 10, 14]},
                 }
    roman_numerals = ["I", "ii", "iii", "IV", "V", "vi", "vii"]
    scale_indices = {0: "I", 2: "ii", 4: "iii", 5: "IV", 7: "V", 9: "vi", 11: "vii"}
    for degree_index, roman in enumerate(roman_numerals):
        chord_root_note = scale_notes[degree_index]; chord_root_name = NOTE_NAMES[chord_root_note % 12]
        triad_key = roman; seventh_key = roman + ("maj7" if roman in ["I", "IV"] else ("7" if roman == "V" else ("m7b5" if roman == "vii" else "m7")))
        if triad_key in chord_defs: pool[f"{chord_root_name}{chord_defs[triad_key]['name']}"] = {'notes': sorted([(chord_root_note + i) for i in chord_defs[triad_key]["intervals"]]), 'function': roman} # Simplified function store
        if seventh_key in chord_defs: pool[f"{chord_root_name}{chord_defs[seventh_key]['name']}"] = {'notes': sorted([(chord_root_note + i) for i in chord_defs[seventh_key]["intervals"]]), 'function': seventh_key} # Simplified function store
        if is_extra:
            ninth_key = roman + ("maj9" if roman in ["I", "IV"] else ("9" if roman == "V" else ("m9b5" if roman == "vii" else "m9")))
            if ninth_key in chord_defs: pool[f"{chord_root_name}{chord_defs[ninth_key]['name']}"] = {'notes': sorted([(chord_root_note + i) for i in chord_defs[ninth_key]["intervals"]])[:6], 'function': ninth_key} # Simplified function store
            # Add other extensions based on the original logic...
    max_notes = 6 if is_extra else 4; return {name: data for name, data in pool.items() if len(data['notes']) <= max_notes}

def generate_chorgi_minor_chord_pool(key_root_name, root_midi_note, complexity="Standard (Triads/7ths)"):
    pool = {}; scale_notes = get_natural_minor_scale_notes(root_midi_note); is_extra = complexity == "Extra (Extensions)"
    # Simplified chord_defs for brevity, original file has full definitions
    chord_defs = { "i": {"name": "m", "intervals": [0, 3, 7]}, "i7": {"name": "m7", "intervals": [0, 3, 7, 10]},
                   "ii": {"name": "dim", "intervals": [0, 3, 6]}, "iiø7": {"name": "m7b5", "intervals": [0, 3, 6, 10]},
                   "III": {"name": "maj", "intervals": [0, 4, 7]}, "IIImaj7": {"name": "maj7", "intervals": [0, 4, 7, 11]},
                   "iv": {"name": "m", "intervals": [0, 3, 7]}, "iv7": {"name": "m7", "intervals": [0, 3, 7, 10]},
                   "v": {"name": "m", "intervals": [0, 3, 7]}, "v7": {"name": "m7", "intervals": [0, 3, 7, 10]},
                   "VI": {"name": "maj", "intervals": [0, 4, 7]}, "VImaj7": {"name": "maj7", "intervals": [0, 4, 7, 11]},
                   "VII": {"name": "maj", "intervals": [0, 4, 7]}, "VII7": {"name": "7", "intervals": [0, 4, 7, 10]},
                   # Harmonic minor V chord
                   "V7(hm)": {"name": "7", "intervals": [0, 4, 7, 10]}, # V7 based on root+7
                   # Extensions (examples)
                   "i9": {"name": "m9", "intervals": [0, 3, 7, 10, 14]}, "V9(hm)": {"name": "9", "intervals": [0, 4, 7, 10, 14]},
                   "V7b9(hm)": {"name": "7b9", "intervals": [0, 4, 7, 10, 13]}, # Example 7b9
                   "iiø9": {"name": "m9b5", "intervals": [0, 3, 6, 10, 14]}, # Example m9b5
                 }
    roman_numerals = ["i", "ii", "III", "iv", "v", "VI", "VII"]
    scale_indices = {0: "i", 2: "ii", 3: "III", 5: "iv", 7: "v", 8: "VI", 10: "VII"}
    for degree_index, roman in enumerate(roman_numerals):
        chord_root_note = scale_notes[degree_index]; chord_root_name = NOTE_NAMES[chord_root_note % 12]
        is_v_chord = (roman == "v"); v_chord_note = root_midi_note + 7
        triad_key = roman
        seventh_key = roman + ("7" if roman == "v" else ("m7b5" if roman == "ii" else ("7" if roman == "VII" else ("maj7" if roman in ["III", "VI"] else "m7"))))
        harmonic_v7_key = "V7(hm)"; harmonic_v9_key = "V9(hm)"; harmonic_v7b9_key = "V7b9(hm)"
        current_func = roman # Store the diatonic function name

        if is_v_chord:
             seventh_key = harmonic_v7_key
             # triad_key = harmonic_v7_key # Don't use V7 as triad
             chord_root_note = v_chord_note # Use harmonic minor root for V
             chord_root_name = NOTE_NAMES[chord_root_note % 12]
             current_func = "V(hm)" # Indicate harmonic minor function

        if triad_key in chord_defs: pool[f"{chord_root_name}{chord_defs[triad_key]['name']}"] = {'notes': sorted([(chord_root_note + i) for i in chord_defs[triad_key]["intervals"]]), 'function': current_func} # Simplified func
        # Use harmonic root for V7
        v7_root_note = v_chord_note if seventh_key == harmonic_v7_key else chord_root_note
        v7_root_name = NOTE_NAMES[v7_root_note % 12] if seventh_key == harmonic_v7_key else chord_root_name
        if seventh_key in chord_defs: pool[f"{v7_root_name}{chord_defs[seventh_key]['name']}"] = {'notes': sorted([(v7_root_note + i) for i in chord_defs[seventh_key]["intervals"]]), 'function': current_func} # Simplified func

        if is_extra:
            ninth_key, alt_ninth_key = None, None
            current_func_ext = current_func # Base function for extensions
            ext_root_note = chord_root_note; ext_root_name = chord_root_name
            if is_v_chord:
                 ninth_key = harmonic_v9_key; alt_ninth_key = harmonic_v7b9_key # Example
                 ext_root_note = v_chord_note; ext_root_name = NOTE_NAMES[ext_root_note % 12]
                 current_func_ext = "V(hm)"
            elif roman == "ii": ninth_key = "iiø9" # Example
            elif roman == "i": ninth_key = "i9"
            # ... other extension logic ...

            if ninth_key and ninth_key in chord_defs: pool[f"{ext_root_name}{chord_defs[ninth_key]['name']}"] = {'notes': sorted([(ext_root_note + i) for i in chord_defs[ninth_key]["intervals"]])[:6], 'function': current_func_ext} # Simplified func
            if alt_ninth_key and alt_ninth_key in chord_defs: pool[f"{ext_root_name}{chord_defs[alt_ninth_key]['name']}"] = {'notes': sorted([(ext_root_note + i) for i in chord_defs[alt_ninth_key]["intervals"]])[:6], 'function': current_func_ext} # Simplified func

    max_notes = 6 if is_extra else 4; return {name: data for name, data in pool.items() if len(data['notes']) <= max_notes}


def generate_jazz_major_chord_pool(key_root_name, root_midi_note, complexity="Standard (Triads/7ths)"):
    pool = {}; scale_notes = get_major_scale_notes(root_midi_note); is_extra = complexity == "Extra (Extensions)"
    # Simplified jazz_chord_defs for brevity
    jazz_chord_defs = { "Imaj7": {"name": "maj7", "intervals": [0, 4, 7, 11]}, "Imaj9": {"name": "maj9", "intervals": [0, 4, 7, 11, 14]},
                        "ii7": {"name": "m7", "intervals": [0, 3, 7, 10]}, "ii9": {"name": "m9", "intervals": [0, 3, 7, 10, 14]},
                        "V7": {"name": "7", "intervals": [0, 4, 7, 10]}, "V9": {"name": "9", "intervals": [0, 4, 7, 10, 14]},
                        "iii7": {"name": "m7", "intervals": [0, 3, 7, 10]},
                        "IVmaj7": {"name": "maj7", "intervals": [0, 4, 7, 11]},
                        "vi7": {"name": "m7", "intervals": [0, 3, 7, 10]},
                        "viiø7": {"name": "m7b5", "intervals": [0, 3, 6, 10]},
                        # Add more jazz chords based on original...
                       }
    roman_numerals = ["I", "ii", "iii", "IV", "V", "vi", "vii"]
    for degree_index, roman in enumerate(roman_numerals):
        chord_root_note = scale_notes[degree_index]; chord_root_name = NOTE_NAMES[chord_root_note % 12]
        seventh_key = roman + ("maj7" if roman in ["I", "IV"] else ("7" if roman == "V" else ("m7b5" if roman == "vii" else "m7")))
        if seventh_key in jazz_chord_defs: pool[f"{chord_root_name}{jazz_chord_defs[seventh_key]['name']}"] = {'notes': sorted([(chord_root_note + i) for i in jazz_chord_defs[seventh_key]["intervals"]]), 'function': seventh_key} # Simplified func
        if is_extra:
            ninth_key = roman + ("maj9" if roman in ["I", "IV"] else ("9" if roman == "V" else ("m9b5" if roman == "vii" else "m9")))
            if ninth_key in jazz_chord_defs: pool[f"{chord_root_name}{jazz_chord_defs[ninth_key]['name']}"] = {'notes': sorted([(chord_root_note + i) for i in jazz_chord_defs[ninth_key]["intervals"]])[:6], 'function': ninth_key} # Simplified func
            # Add other extensions based on the original logic...
    max_notes = 6 if is_extra else 4; return {name: data for name, data in pool.items() if len(data['notes']) <= max_notes}


def generate_jazz_minor_chord_pool(key_root_name, root_midi_note, complexity="Standard (Triads/7ths)"):
    pool = {}; scale_notes = get_natural_minor_scale_notes(root_midi_note); is_extra = complexity == "Extra (Extensions)"
    # Simplified jazz_chord_defs for brevity
    jazz_chord_defs = { "i7": {"name": "m7", "intervals": [0, 3, 7, 10]}, "i9": {"name": "m9", "intervals": [0, 3, 7, 10, 14]},
                        "iiø7": {"name": "m7b5", "intervals": [0, 3, 6, 10]}, "iiø9": {"name": "m9b5", "intervals": [0, 3, 6, 10, 14]}, # Check intervals
                        "V7(hm)": {"name": "7", "intervals": [0, 4, 7, 10]}, "V9(hm)": {"name": "9", "intervals": [0, 4, 7, 10, 14]},
                        "IIImaj7": {"name": "maj7", "intervals": [0, 4, 7, 11]},
                        "iv7": {"name": "m7", "intervals": [0, 3, 7, 10]},
                        "VImaj7": {"name": "maj7", "intervals": [0, 4, 7, 11]},
                        "VII7": {"name": "7", "intervals": [0, 4, 7, 10]}, # Often dominant quality in jazz minor
                        "V7b9(hm)": {"name": "7b9", "intervals": [0, 4, 7, 10, 13]},
                        # Add more jazz chords based on original...
                      }
    roman_numerals = ["i", "ii", "III", "iv", "v", "VI", "VII"]
    v_chord_note_hm = root_midi_note + 7; vii_chord_note_hm = root_midi_note + 11 # Correct note for VII? Might be root+10 or root+11 depending on scale

    for degree_index, roman in enumerate(roman_numerals):
        chord_root_note_nat = scale_notes[degree_index]; chord_root_name_nat = NOTE_NAMES[chord_root_note_nat % 12]
        chord_root_note, chord_root_name = chord_root_note_nat, chord_root_name_nat
        is_v_chord = (roman == "v"); is_vii_chord = (roman == "VII"); is_ii_chord = (roman == "ii")
        current_func = roman

        seventh_key = "V7(hm)" if is_v_chord else ("iiø7" if is_ii_chord else ("VII7" if is_vii_chord else roman + ("maj7" if roman in ["III", "VI"] else "m7")))
        current_root = chord_root_note; current_name = chord_root_name
        if seventh_key == "V7(hm)": current_root, current_name, current_func = v_chord_note_hm, NOTE_NAMES[v_chord_note_hm % 12], "V(hm)"
        # VII chord root might need adjustment based on jazz context (often uses Nat Minor VII root + Dom7 quality)
        # if seventh_key == "VII7": current_root, current_name = scale_notes[6], NOTE_NAMES[scale_notes[6] % 12] # Use natural minor root for VII7

        if seventh_key in jazz_chord_defs: pool[f"{current_name}{jazz_chord_defs[seventh_key]['name']}"] = {'notes': sorted([(current_root + i) for i in jazz_chord_defs[seventh_key]["intervals"]]), 'function': current_func} # Simplified func

        if is_extra:
            ninth_key, alt_keys = None, []
            current_func_ext = current_func
            ext_root_note = current_root; ext_root_name = current_name # Use potentially adjusted root from above
            if is_v_chord: ninth_key, alt_keys, current_func_ext = "V9(hm)", ["V7b9(hm)"], "V(hm)"; # ext_root_note, ext_root_name = v_chord_note_hm, NOTE_NAMES[v_chord_note_hm % 12] # Already set
            elif is_ii_chord: ninth_key = "iiø9"
            elif roman == "i": ninth_key = "i9"
            # ... other extension logic ...

            if ninth_key and ninth_key in jazz_chord_defs: pool[f"{ext_root_name}{jazz_chord_defs[ninth_key]['name']}"] = {'notes': sorted([(ext_root_note + i) for i in jazz_chord_defs[ninth_key]["intervals"]])[:6], 'function': current_func_ext} # Simplified func
            for alt_k in alt_keys:
                 if alt_k and alt_k in jazz_chord_defs: pool[f"{ext_root_name}{jazz_chord_defs[alt_k]['name']}"] = {'notes': sorted([(ext_root_note + i) for i in jazz_chord_defs[alt_k]["intervals"]])[:6], 'function': current_func_ext} # Simplified func

    max_notes = 6 if is_extra else 4; return {name: data for name, data in pool.items() if len(data['notes']) <= max_notes}

# --- ADDED: Blues Chord Pool Generation ---
def generate_blues_chord_pool(key_root_name, root_midi_note, key_type="major"):
    """Generates a specific blues chord pool (I7, IV7, V7 or i7, iv7, V7)."""
    pool = {}
    root_note_index = NOTE_NAMES.index(key_root_name)

    if key_type == "major":
        dom7_intervals = [0, 4, 7, 10]
        # I7
        i_root_note = root_midi_note
        i_root_name = key_root_name
        pool[f"{i_root_name}7"] = {'notes': sorted([(i_root_note + i) for i in dom7_intervals]), 'function': 'I7'} # Use specific function
        # IV7
        iv_root_note = root_midi_note + 5
        iv_root_name = NOTE_NAMES[iv_root_note % 12]
        pool[f"{iv_root_name}7"] = {'notes': sorted([(iv_root_note + i) for i in dom7_intervals]), 'function': 'IV7'}
        # V7
        v_root_note = root_midi_note + 7
        v_root_name = NOTE_NAMES[v_root_note % 12]
        pool[f"{v_root_name}7"] = {'notes': sorted([(v_root_note + i) for i in dom7_intervals]), 'function': 'V7'}
    else: # Minor Blues: i7, iv7, V7 (Dominant V)
        m7_intervals = [0, 3, 7, 10]
        dom7_intervals = [0, 4, 7, 10] # For the V chord
        # i7
        i_root_note = root_midi_note
        i_root_name = key_root_name
        pool[f"{i_root_name}m7"] = {'notes': sorted([(i_root_note + i) for i in m7_intervals]), 'function': 'i7'}
        # iv7
        iv_root_note = root_midi_note + 5
        iv_root_name = NOTE_NAMES[iv_root_note % 12]
        pool[f"{iv_root_name}m7"] = {'notes': sorted([(iv_root_note + i) for i in m7_intervals]), 'function': 'iv7'}
        # V7 (Dominant)
        v_chord_root_note = root_midi_note + 7 # Root of the V chord itself
        v_chord_root_name = NOTE_NAMES[v_chord_root_note % 12]
        pool[f"{v_chord_root_name}7"] = {'notes': sorted([(v_chord_root_note + i) for i in dom7_intervals]), 'function': 'V7'}

    return pool


# --- NEW: Helper to find chords by function ---
def _find_chord_by_function(pool, function_target, key_type, prefer_seventh=True):
    """Finds chord names in the pool matching a roman numeral function."""
    matches = []
    # Normalize function_target (e.g., V(hm) -> V)
    base_function_target = function_target.split('(')[0]

    for name, data in pool.items():
        # Normalize pool function (e.g. vii°7(hm) -> vii)
        pool_func = data.get('function', 'Unknown')
        base_pool_func = pool_func.split('(')[0]
        # Basic match
        if base_pool_func.lower() == base_function_target.lower():
            matches.append(name)

    if not matches:
        # print(f"Warning: Could not find chord for function '{function_target}'")
        return None # Or return a default?

    # Preference logic (e.g., prefer V7 over Vmaj)
    if prefer_seventh:
        sevenths = [m for m in matches if '7' in m or '9' in m or '11' in m or '13' in m]
        if sevenths: return random.choice(sevenths)

    # Fallback to any match
    if matches: # Ensure matches is not empty before choosing
        return random.choice(matches)
    else:
        return None # Explicitly return None if no matches found


# --- Melody Generation Functions ---
# (Melody generation functions remain largely unchanged, ensure they use the updated
# progression_data structure: chord_name, chord_notes_original, _, _, duration_beats)
def get_stepwise_notes(current_note, extended_scale, max_step=2):
    """Finds scale notes within max_step degrees of current_note."""
    possible_notes = [];
    if not extended_scale: return [] # Safety check
    try:
        closest_note = min(extended_scale, key=lambda x: abs(x - current_note))
        current_idx = extended_scale.index(closest_note)
        for step in range(-max_step, max_step + 1):
            if step == 0: continue
            idx = current_idx + step
            if 0 <= idx < len(extended_scale):
                 possible_notes.append(extended_scale[idx])
    except ValueError:
        pass # current_note might be outside the scale range slightly
    return possible_notes

def generate_melody_chord_focus(progression_data, scale_notes, melody_style, melody_speed, melody_octave, instrument_type="None"):
    melody_data = []; current_abs_time_melody = 0.0; melody_octave_shift = 12 if melody_octave == "Mid" else 24
    staccato_duration = 0.15; melody_rhythm_placements = get_melody_rhythm_placements(melody_speed); last_melody_note = None
    scale_note_pcs = {n % 12 for n in scale_notes} if scale_notes else set()
    if not scale_notes:
        print("Warning: Chord Focus Melody generation cannot proceed without scale notes.")
        return []
    extended_scale = sorted(list(set([n + oct for n in scale_notes for oct in [-24, -12, 0, 12, 24, 36]])))
    min_pitch = 60 if melody_octave == "Mid" else 72; max_pitch = 84 if melody_octave == "Mid" else 96

    # Instrument-specific adjustments (basic example)
    chord_tone_weight = 0.7
    stepwise_weight = 0.3
    if instrument_type == "Synth Lead":
        chord_tone_weight = 0.6
        stepwise_weight = 0.4
    elif instrument_type in ["Keys", "Piano"]:
        chord_tone_weight = 0.8
    elif instrument_type == "Pluck":
        staccato_duration = 0.1 # Shorter default for plucks
        if melody_style == "Legato": # Force staccato for plucks
            melody_style = "Staccato"

    current_chord_idx = 0
    while current_chord_idx < len(progression_data):
        chord_name, chord_notes_original, _, _, duration_beats = progression_data[current_chord_idx]
        chord_start_time = current_abs_time_melody

        if not chord_notes_original or duration_beats <= 0: # Added duration check
             current_abs_time_melody += duration_beats if duration_beats > 0 else 1.0 # Advance time even if chord invalid
             current_chord_idx += 1
             continue

        current_time_in_chord = 0.0
        num_beats_in_chord = int(duration_beats + 0.5)
        melody_chord_notes = transpose_notes(chord_notes_original, melody_octave_shift)
        diatonic_melody_chord_notes = [n for n in melody_chord_notes if n % 12 in scale_note_pcs]

        for beat in range(num_beats_in_chord):
            if current_time_in_chord >= duration_beats - 0.01: break

            rhythm_placement = random.choice(melody_rhythm_placements) if melody_rhythm_placements else [(0, 1.0)]
            beat_start_time_relative = beat

            for start_offset, beat_fraction_duration in rhythm_placement:
                note_relative_start_in_beat = start_offset
                note_absolute_start_in_chord = beat_start_time_relative + note_relative_start_in_beat

                if note_absolute_start_in_chord >= duration_beats - 0.01: continue

                note_start_time_abs = chord_start_time + note_absolute_start_in_chord
                time_remaining_in_chord = duration_beats - note_absolute_start_in_chord

                actual_duration = staccato_duration if melody_style == "Staccato" else beat_fraction_duration
                actual_duration = min(actual_duration, time_remaining_in_chord)

                if actual_duration <= 0.01: continue

                possible_notes = []
                # Adjust weights based on instrument type
                if random.random() < chord_tone_weight and diatonic_melody_chord_notes:
                    possible_notes.extend(diatonic_melody_chord_notes * 3)
                if last_melody_note is not None and extended_scale and random.random() < stepwise_weight : # Added weight check
                    possible_notes.extend(get_stepwise_notes(last_melody_note, extended_scale, max_step=2))

                # Fallback if weights didn't yield notes
                if not possible_notes:
                    possible_notes = diatonic_melody_chord_notes or ([random.choice(scale_notes) + melody_octave_shift] if scale_notes else [60+melody_octave_shift])

                if not possible_notes: continue

                pitch = random.choice(possible_notes)
                while pitch < min_pitch: pitch += 12
                while pitch > max_pitch: pitch -= 12

                if pitch % 12 not in scale_note_pcs:
                    try:
                        closest_diatonic_pc = min(scale_note_pcs, key=lambda pc: min(abs(pitch % 12 - pc), abs(pitch % 12 - pc - 12), abs(pitch % 12 - pc + 12)))
                        pitch = (pitch // 12) * 12 + closest_diatonic_pc
                        while pitch < min_pitch: pitch += 12
                        while pitch > max_pitch: pitch -= 12
                        if pitch % 12 not in scale_note_pcs: pitch = None
                    except ValueError:
                        pitch = None

                if pitch is not None:
                    melody_data.append((pitch, note_start_time_abs, actual_duration));
                    last_melody_note = pitch

            current_time_in_chord = beat + 1.0

        current_abs_time_melody += duration_beats
        current_chord_idx += 1
    return melody_data

def generate_melody_scale_walker(progression_data, scale_notes, melody_style, melody_speed, melody_octave, instrument_type="None"):
    melody_data = []; current_abs_time_melody = 0.0; melody_octave_shift = 12 if melody_octave == "Mid" else 24
    staccato_duration = 0.15; melody_rhythm_placements = get_melody_rhythm_placements(melody_speed)
    last_melody_note = None; last_direction = 0; direction_change_prob = 0.3;
    scale_note_pcs = {n % 12 for n in scale_notes} if scale_notes else set()
    if not scale_notes: print("Warning: Scale Walker Melody generation cannot proceed without scale notes."); return []
    min_pitch_range = 48 if melody_octave == "Mid" else 60; max_pitch_range = 96 if melody_octave == "Mid" else 108
    extended_scale = sorted(list(set([n + oct_shift for n in scale_notes for oct_shift in [-24, -12, 0, 12, 24, 36] if min_pitch_range <= n + oct_shift <= max_pitch_range])))
    if not extended_scale: extended_scale = [60, 62, 64, 65, 67, 69, 71]; scale_note_pcs = {n%12 for n in extended_scale};
    target_min_pitch = 60 if melody_octave == "Mid" else 72; target_max_pitch = 84 if melody_octave == "Mid" else 96
    possible_starts = [n for n in extended_scale if target_min_pitch <= n <= target_max_pitch]
    last_melody_note = random.choice(possible_starts) if possible_starts else (random.choice(extended_scale) if extended_scale else 60 + melody_octave_shift)

    # Instrument adjustments
    if instrument_type == "Pluck":
         staccato_duration = 0.1
         if melody_style == "Legato": melody_style = "Staccato"
    elif instrument_type == "Synth Lead":
         direction_change_prob = 0.4 # More likely to change direction

    current_chord_idx = 0
    while current_chord_idx < len(progression_data):
        chord_name, chord_notes_original, _, _, duration_beats = progression_data[current_chord_idx]
        chord_start_time = current_abs_time_melody

        if not chord_notes_original or duration_beats <= 0: # Added duration check
             current_abs_time_melody += duration_beats if duration_beats > 0 else 1.0
             current_chord_idx += 1
             continue

        current_time_in_chord = 0.0
        num_beats_in_chord = int(duration_beats + 0.5)
        melody_chord_notes = transpose_notes(chord_notes_original, melody_octave_shift)
        diatonic_melody_chord_notes = [n for n in melody_chord_notes if n % 12 in scale_note_pcs]

        for beat in range(num_beats_in_chord):
            if current_time_in_chord >= duration_beats - 0.01: break

            rhythm_placement = random.choice(melody_rhythm_placements) if melody_rhythm_placements else [(0, 1.0)]
            beat_start_time_relative = beat

            for start_offset, beat_fraction_duration in rhythm_placement:
                note_relative_start_in_beat = start_offset
                note_absolute_start_in_chord = beat_start_time_relative + note_relative_start_in_beat

                if note_absolute_start_in_chord >= duration_beats - 0.01: continue

                note_start_time_abs = chord_start_time + note_absolute_start_in_chord
                time_remaining_in_chord = duration_beats - note_absolute_start_in_chord

                actual_duration = staccato_duration if melody_style == "Staccato" else beat_fraction_duration
                actual_duration = min(actual_duration, time_remaining_in_chord)
                if actual_duration <= 0.01: continue

                possible_next_notes = []; pitch = None
                if last_melody_note is not None and extended_scale:
                    try:
                        closest_last = min(extended_scale, key=lambda x: abs(x - last_melody_note));
                        last_idx = extended_scale.index(closest_last)
                        if random.random() < direction_change_prob: last_direction *= -1; last_direction = last_direction or random.choice([-1, 1])
                        elif last_direction == 0: last_direction = random.choice([-1, 1])

                        pref_steps, other_steps = [], []
                        for step in [-2, -1, 1, 2]:
                            idx = last_idx + step
                            if 0 <= idx < len(extended_scale):
                                note = extended_scale[idx]
                                if (step > 0 and last_direction == 1) or (step < 0 and last_direction == -1): pref_steps.append(note)
                                else: other_steps.append(note)
                        possible_next_notes.extend(pref_steps * 5); possible_next_notes.extend(other_steps * 2)
                        if random.random() < 0.2 and diatonic_melody_chord_notes: possible_next_notes.extend(diatonic_melody_chord_notes)
                    except ValueError: possible_next_notes = diatonic_melody_chord_notes or ([random.choice(extended_scale)] if extended_scale else [])
                else: possible_next_notes = diatonic_melody_chord_notes or ([random.choice(extended_scale)] if extended_scale else [])

                if not possible_next_notes: pitch = (random.choice(scale_notes) if scale_notes else 60) + melody_octave_shift
                else: pitch = random.choice(possible_next_notes)

                if last_melody_note is not None and pitch is not None: last_direction = 1 if pitch > last_melody_note else (-1 if pitch < last_melody_note else last_direction)

                while pitch < target_min_pitch: pitch += 12
                while pitch > target_max_pitch: pitch -= 12
                if pitch % 12 not in scale_note_pcs:
                    try:
                        closest_diatonic_pc = min(scale_note_pcs, key=lambda pc: min(abs(pitch % 12 - pc), abs(pitch % 12 - pc - 12), abs(pitch % 12 - pc + 12)))
                        pitch = (pitch // 12) * 12 + closest_diatonic_pc
                        while pitch < target_min_pitch: pitch += 12
                        while pitch > target_max_pitch: pitch -= 12
                        if pitch % 12 not in scale_note_pcs: pitch = None
                    except ValueError: pitch = None


                if pitch is not None:
                    melody_data.append((pitch, note_start_time_abs, actual_duration));
                    last_melody_note = pitch

            current_time_in_chord = beat + 1.0

        current_abs_time_melody += duration_beats
        current_chord_idx += 1
    return melody_data

def generate_melody_experimental(progression_data, scale_notes, melody_style, melody_speed, melody_octave, instrument_type="None"):
    melody_data = []; current_abs_time_melody = 0.0; melody_octave_shift = 12 if melody_octave == "Mid" else 24
    staccato_duration = 0.15;
    # Motifs define total duration, not just per-bar patterns anymore
    if melody_speed == "Slow": motifs = [[1.0, 1.0, 1.0, 1.0], [2.0, 1.0, 1.0], [2.0, 2.0], [1.5, 1.5, 1.0], [4.0]]
    elif melody_speed == "Fast": motifs = [[0.5]*4, [0.25]*8, [0.75, 0.25]*2, [0.5, 0.25, 0.25]*2, [0.333]*6] # Shorter motifs for faster speed
    else: motifs = [[0.5, 0.5, 1.0, 1.0], [1.0, 0.5, 0.5, 1.0], [1.0, 1.0, 0.5, 0.5], [1.0]*2]

    if instrument_type == "Pluck":
        staccato_duration = 0.1
        if melody_style == "Legato": melody_style = "Staccato"
        motifs = [[0.25]*4, [0.5, 0.25, 0.25], [0.125]*8]

    last_melody_note = None; scale_note_pcs = {n % 12 for n in scale_notes} if scale_notes else set()
    if not scale_notes: print("Warning: Experimental Melody generation cannot proceed without scale notes."); return []
    min_ext_pitch = 48 if melody_octave == "Mid" else 60; max_ext_pitch = 96 if melody_octave == "Mid" else 108
    extended_scale = sorted(list(set([n + oct for n in scale_notes for oct in [-12, 0, 12, 24] if min_ext_pitch <= n+oct <= max_ext_pitch])))
    if not extended_scale: extended_scale = [60, 62, 64, 65, 67, 69, 71]
    min_pitch = 60 if melody_octave == "Mid" else 72; max_pitch = 84 if melody_octave == "Mid" else 96

    current_chord_idx = 0
    while current_chord_idx < len(progression_data):
        chord_name, chord_notes_original, _, _, duration_beats = progression_data[current_chord_idx]
        chord_start_time = current_abs_time_melody

        if not chord_notes_original or duration_beats <= 0: # Added duration check
             current_abs_time_melody += duration_beats if duration_beats > 0 else 1.0
             current_chord_idx += 1
             continue

        current_time_in_chord = 0.0
        melody_chord_notes = transpose_notes(chord_notes_original, melody_octave_shift)
        diatonic_melody_chord_notes = [n for n in melody_chord_notes if n % 12 in scale_note_pcs and min_pitch <= n <= max_pitch]
        chosen_motif = random.choice(motifs); motif_index = 0
        chord_tone_index = random.randint(0, max(0, len(diatonic_melody_chord_notes)-1)) if diatonic_melody_chord_notes else 0

        while current_time_in_chord < duration_beats - 0.01:
            duration = chosen_motif[motif_index % len(chosen_motif)];
            time_remaining_in_chord = duration_beats - current_time_in_chord
            if duration > time_remaining_in_chord + 0.01 : duration = time_remaining_in_chord

            note_start_time_abs = chord_start_time + current_time_in_chord
            actual_duration = staccato_duration if melody_style == "Staccato" else duration
            actual_duration = min(actual_duration, time_remaining_in_chord)

            if actual_duration <= 0.01:
                current_time_in_chord += duration
                motif_index += 1
                continue

            pitch = None; possible_notes = []
            if diatonic_melody_chord_notes:
                possible_notes.extend([diatonic_melody_chord_notes[chord_tone_index % len(diatonic_melody_chord_notes)]] * 5)
                chord_tone_index += 1
            if last_melody_note is not None and extended_scale and random.random() < 0.3:
                 possible_notes.extend(get_stepwise_notes(last_melody_note, extended_scale, max_step=3))

            if not possible_notes: pitch = (random.choice(scale_notes) if scale_notes else 60) + melody_octave_shift
            else: pitch = random.choice(possible_notes)

            if pitch is not None:
                while pitch < min_pitch: pitch += 12
                while pitch > max_pitch: pitch -= 12
                if pitch % 12 not in scale_note_pcs:
                    try:
                        closest_diatonic_pc = min(scale_note_pcs, key=lambda pc: min(abs(pitch % 12 - pc), abs(pitch % 12 - pc - 12), abs(pitch % 12 - pc + 12)))
                        pitch = (pitch // 12) * 12 + closest_diatonic_pc
                        while pitch < min_pitch: pitch += 12
                        while pitch > max_pitch: pitch -= 12
                        if pitch % 12 not in scale_note_pcs: pitch = None
                    except ValueError: pitch = None


                if pitch is not None:
                    melody_data.append((pitch, note_start_time_abs, actual_duration));
                    last_melody_note = pitch

            current_time_in_chord += duration; motif_index += 1

        current_abs_time_melody += duration_beats
        current_chord_idx += 1
    return melody_data

def generate_melody_leaps_steps(progression_data, scale_notes, melody_style, melody_speed, melody_octave, instrument_type="None"):
    melody_data = []; current_abs_time_melody = 0.0; melody_octave_shift = 12 if melody_octave == "Mid" else 24
    staccato_duration = 0.15; melody_rhythm_placements = get_melody_rhythm_placements(melody_speed)
    last_melody_note = None; leap_probability = 0.45;
    scale_note_pcs = {n % 12 for n in scale_notes} if scale_notes else set()
    if not scale_notes: print("Warning: Leaps & Steps Melody generation cannot proceed without scale notes."); return []
    min_pitch_range = 48 if melody_octave == "Mid" else 60; max_pitch_range = 96 if melody_octave == "Mid" else 108
    extended_scale = sorted(list(set([n + oct for n in scale_notes for oct in [-24, -12, 0, 12, 24, 36] if min_pitch_range <= n + oct <= max_pitch_range])))
    if not extended_scale: extended_scale = [60, 62, 64, 65, 67, 69, 71]; scale_note_pcs = {n%12 for n in extended_scale};
    target_min_pitch = 60 if melody_octave == "Mid" else 72; target_max_pitch = 84 if melody_octave == "Mid" else 96
    possible_starts = [n for n in extended_scale if target_min_pitch <= n <= target_max_pitch]
    last_melody_note = random.choice(possible_starts) if possible_starts else (random.choice(extended_scale) if extended_scale else 60 + melody_octave_shift)

    # Instrument adjustments
    if instrument_type == "Synth Lead":
        leap_probability = 0.6 # More leaps
    elif instrument_type == "Piano":
        leap_probability = 0.35 # Fewer leaps
    elif instrument_type == "Pluck":
         staccato_duration = 0.1
         if melody_style == "Legato": melody_style = "Staccato"

    current_chord_idx = 0
    while current_chord_idx < len(progression_data):
        chord_name, chord_notes_original, _, _, duration_beats = progression_data[current_chord_idx]
        chord_start_time = current_abs_time_melody

        if not chord_notes_original or duration_beats <= 0: # Added duration check
             current_abs_time_melody += duration_beats if duration_beats > 0 else 1.0
             current_chord_idx += 1
             continue

        current_time_in_chord = 0.0
        num_beats_in_chord = int(duration_beats + 0.5)
        melody_chord_notes = transpose_notes(chord_notes_original, melody_octave_shift)
        diatonic_leap_targets = [n for n in melody_chord_notes if n % 12 in scale_note_pcs and target_min_pitch <= n <= target_max_pitch]

        for beat in range(num_beats_in_chord):
            if current_time_in_chord >= duration_beats - 0.01: break

            rhythm_placement = random.choice(melody_rhythm_placements) if melody_rhythm_placements else [(0, 1.0)]
            beat_start_time_relative = beat

            for start_offset, beat_fraction_duration in rhythm_placement:
                note_relative_start_in_beat = start_offset
                note_absolute_start_in_chord = beat_start_time_relative + note_relative_start_in_beat

                if note_absolute_start_in_chord >= duration_beats - 0.01: continue

                note_start_time_abs = chord_start_time + note_absolute_start_in_chord
                time_remaining_in_chord = duration_beats - note_absolute_start_in_chord

                actual_duration = staccato_duration if melody_style == "Staccato" else beat_fraction_duration
                actual_duration = min(actual_duration, time_remaining_in_chord)
                if actual_duration <= 0.01: continue

                possible_next_notes = []; pitch = None
                use_leap = (random.random() < leap_probability) and diatonic_leap_targets and last_melody_note is not None

                if use_leap:
                    possible_next_notes = [n for n in diatonic_leap_targets if n != last_melody_note]
                    if not possible_next_notes: possible_next_notes = diatonic_leap_targets
                else:
                    if last_melody_note is not None and extended_scale: possible_next_notes = get_stepwise_notes(last_melody_note, extended_scale, max_step=1)

                if not possible_next_notes: possible_next_notes = diatonic_leap_targets or ([random.choice(extended_scale)] if extended_scale else [])

                if not possible_next_notes: pitch = (random.choice(scale_notes) if scale_notes else 60) + melody_octave_shift
                else: pitch = random.choice(possible_next_notes)

                while pitch < target_min_pitch: pitch += 12
                while pitch > target_max_pitch: pitch -= 12
                if pitch % 12 not in scale_note_pcs:
                    try:
                        closest_diatonic_pc = min(scale_note_pcs, key=lambda pc: min(abs(pitch % 12 - pc), abs(pitch % 12 - pc - 12), abs(pitch % 12 - pc + 12)))
                        pitch = (pitch // 12) * 12 + closest_diatonic_pc
                        while pitch < target_min_pitch: pitch += 12
                        while pitch > target_max_pitch: pitch -= 12
                        if pitch % 12 not in scale_note_pcs: pitch = None
                    except ValueError: pitch = None


                if pitch is not None:
                    melody_data.append((pitch, note_start_time_abs, actual_duration));
                    last_melody_note = pitch

            current_time_in_chord = beat + 1.0

        current_abs_time_melody += duration_beats
        current_chord_idx += 1
    return melody_data

def generate_melody_minimalist(progression_data, scale_notes, melody_style, melody_speed, melody_octave, instrument_type="None"):
    melody_data = []; current_abs_time_melody = 0.0; melody_octave_shift = 12 if melody_octave == "Mid" else 24
    staccato_duration = 0.15;
    # Rhythm options are durations relative to beats
    if melody_speed == "Slow": rhythm_options = [[(0, 2.0)], [(0, 1.0)], [(0, 4.0)], [(0.5, 1.0)], [(1.0, 2.0)]]
    elif melody_speed == "Fast": rhythm_options = [[(0, 0.5)], [(0, 0.25)], [(0, 1.0)], [(0.25, 0.5)], [(0.75, 0.25)]]
    else: rhythm_options = [[(0, 1.0)], [(0, 0.5), (0.5, 0.5)], [(0, 2.0)], [(0.5, 1.0)], [(1.0, 1.0)]]

    last_melody_note = None; rest_probability = 0.35;
    scale_note_pcs = {n % 12 for n in scale_notes} if scale_notes else set()
    if not scale_notes: print("Warning: Minimalist Melody generation cannot proceed without scale notes."); return []
    target_min_pitch = 60 if melody_octave == "Mid" else 72; target_max_pitch = 84 if melody_octave == "Mid" else 96

    # Instrument adjustments
    if instrument_type in ["Piano", "Keys"]:
        rest_probability = 0.45 # More rests for piano/keys
    elif instrument_type == "Pluck":
        rest_probability = 0.20 # Fewer rests for pluck
        staccato_duration = 0.1
        if melody_style == "Legato": melody_style = "Staccato"


    current_chord_idx = 0
    while current_chord_idx < len(progression_data):
        chord_name, chord_notes_original, _, _, duration_beats = progression_data[current_chord_idx]
        chord_start_time = current_abs_time_melody

        if not chord_notes_original or duration_beats <= 0: # Added duration check
             current_abs_time_melody += duration_beats if duration_beats > 0 else 1.0
             current_chord_idx += 1
             continue

        current_time_in_chord = 0.0
        melody_chord_notes = transpose_notes(chord_notes_original, melody_octave_shift)
        stable_indices = [0, 2, 4] # R, 3, 5 approx
        # FIX: Correct list comprehension syntax for diatonic_stable_tones
        diatonic_stable_tones = [n for i, n in enumerate(melody_chord_notes) if i < len(stable_indices) and i in stable_indices and n % 12 in scale_note_pcs and target_min_pitch <= n <= target_max_pitch]
        if not diatonic_stable_tones: diatonic_stable_tones = [n for n in melody_chord_notes if n % 12 in scale_note_pcs and target_min_pitch <= n <= target_max_pitch]
        if not diatonic_stable_tones:
            diatonic_stable_tones = [(n + melody_octave_shift) for n in scale_notes if target_min_pitch <= n+melody_octave_shift <= target_max_pitch]
            if not diatonic_stable_tones: diatonic_stable_tones = [60 + melody_octave_shift]

        while current_time_in_chord < duration_beats - 0.01:
            if random.random() < rest_probability:
                rest_duration = random.choice([0.5, 1.0, 1.5, 2.0])
                time_remaining = duration_beats - current_time_in_chord
                current_time_in_chord += min(rest_duration, time_remaining)
                continue

            rhythm_placement = random.choice(rhythm_options) if rhythm_options else [(0, 1.0)];
            total_rhythm_dur = sum(d for _,d in rhythm_placement)
            notes_played_in_pattern = 0; pattern_start_in_chord = current_time_in_chord

            for start_offset, beat_fraction_duration in rhythm_placement:
                note_start_in_chord = pattern_start_in_chord + start_offset;
                time_remaining_in_chord = duration_beats - note_start_in_chord
                if note_start_in_chord >= duration_beats - 0.01: break

                note_start_time_abs = chord_start_time + note_start_in_chord
                actual_duration = staccato_duration if melody_style == "Staccato" else beat_fraction_duration
                actual_duration = min(actual_duration, time_remaining_in_chord)
                if actual_duration <= 0.01: continue

                pitch = random.choice(diatonic_stable_tones)
                while pitch < target_min_pitch: pitch += 12
                while pitch > target_max_pitch: pitch -= 12
                if pitch % 12 not in scale_note_pcs:
                    try:
                        closest_diatonic_pc = min(scale_note_pcs, key=lambda pc: min(abs(pitch % 12 - pc), abs(pitch % 12 - pc - 12), abs(pitch % 12 - pc + 12)))
                        pitch = (pitch // 12) * 12 + closest_diatonic_pc
                        while pitch < target_min_pitch: pitch += 12
                        while pitch > target_max_pitch: pitch -= 12
                        if pitch % 12 not in scale_note_pcs: pitch = None
                    except ValueError: pitch = None

                if pitch is not None:
                    melody_data.append((pitch, note_start_time_abs, actual_duration));
                    last_melody_note = pitch
                    notes_played_in_pattern += 1

            # Advance time by the duration of the rhythmic pattern used
            current_time_in_chord = pattern_start_in_chord + total_rhythm_dur
            current_time_in_chord = min(current_time_in_chord, duration_beats) # Clamp to chord boundary

            # Adjust rest probability dynamically
            if notes_played_in_pattern == 0: rest_probability = min(0.8, rest_probability + 0.1)
            else: rest_probability = 0.35 # Reset base rest probability


        current_abs_time_melody += duration_beats
        current_chord_idx += 1
    return melody_data

def generate_melody_sustained_lead(progression_data, scale_notes, melody_style, melody_speed, melody_octave, instrument_type="None"):
    melody_data = []; current_abs_time_melody = 0.0; melody_octave_shift = 12 if melody_octave == "Mid" else 24
    staccato_duration = 0.15;
    # Rhythms relative to chord duration
    if melody_speed == "Slow": rhythm_patterns = [[(0, 1.0)], [(0, 0.5), (0.5, 0.5)], [(0, 0.75), (0.75, 0.25)]] # Fractions of total duration
    elif melody_speed == "Fast": rhythm_patterns = [[(0, 0.25)]*4, [(0, 0.5), (0.5, 0.25), (0.75, 0.25)]*2, [(0, 1.0)]]
    else: rhythm_patterns = [[(0, 0.5)], [(0, 0.25)]*2, [(0, 0.33), (0.33, 0.33), (0.66, 0.34)]] # Approx thirds

    last_melody_note = None; scale_note_pcs = {n % 12 for n in scale_notes} if scale_notes else set()
    if not scale_notes: print("Warning: Sustained Lead Melody generation cannot proceed without scale notes."); return []
    target_min_pitch = 60 if melody_octave == "Mid" else 72; target_max_pitch = 84 if melody_octave == "Mid" else 96

    # Instrument adjustments
    if instrument_type == "Pluck": # Sustained lead doesn't make much sense for plucks
         melody_style = "Staccato" # Force staccato
         staccato_duration = 0.1
         rhythm_patterns = [[(0, 0.25)]*4, [(0, 0.125)]*8] # Use shorter rhythms


    current_chord_idx = 0
    while current_chord_idx < len(progression_data):
        chord_name, chord_notes_original, _, root_note_for_bass, duration_beats = progression_data[current_chord_idx]
        chord_start_time = current_abs_time_melody

        if not chord_notes_original or root_note_for_bass is None or duration_beats <= 0: # Added duration check
            current_abs_time_melody += duration_beats if duration_beats > 0 else 1.0
            current_chord_idx += 1
            continue

        melody_chord_notes = transpose_notes(chord_notes_original, melody_octave_shift)
        diatonic_melody_chord_notes = [n for n in melody_chord_notes if n % 12 in scale_note_pcs and target_min_pitch <= n <= target_max_pitch]
        target_pitch_options = [n for n in transpose_notes([root_note_for_bass], melody_octave_shift) if n % 12 in scale_note_pcs and target_min_pitch <= n <= target_max_pitch]
        if not target_pitch_options:
            target_pitch = random.choice(diatonic_melody_chord_notes) if diatonic_melody_chord_notes \
                      else ((random.choice(scale_notes) if scale_notes else 60) + melody_octave_shift)
        else: target_pitch = target_pitch_options[0]

        rhythm_placement = random.choice(rhythm_patterns) if rhythm_patterns else [(0, 1.0)]

        for start_frac, dur_frac in rhythm_placement:
            note_start_in_chord = duration_beats * start_frac
            note_dur_beats = duration_beats * dur_frac

            note_start_time_abs = chord_start_time + note_start_in_chord
            time_remaining_in_chord = duration_beats - note_start_in_chord

            actual_duration = staccato_duration if melody_style == "Staccato" else note_dur_beats
            actual_duration = min(actual_duration, time_remaining_in_chord)
            if actual_duration <= 0.01: continue

            pitch = target_pitch
            # Slightly more chance to deviate for non-piano/keys
            deviation_prob = 0.3 if instrument_type not in ["Piano", "Keys"] else 0.2
            if random.random() < deviation_prob and len(diatonic_melody_chord_notes) > 1:
                 other_diatonic_tones = [n for n in diatonic_melody_chord_notes if n != target_pitch]
                 if other_diatonic_tones: pitch = random.choice(other_diatonic_tones)
            elif pitch is None or pitch % 12 not in scale_note_pcs: pitch = (random.choice(scale_notes) if scale_notes else 60) + melody_octave_shift

            while pitch < target_min_pitch: pitch += 12
            while pitch > target_max_pitch: pitch -= 12
            if pitch % 12 not in scale_note_pcs:
                try:
                    closest_diatonic_pc = min(scale_note_pcs, key=lambda pc: min(abs(pitch % 12 - pc), abs(pitch % 12 - pc - 12), abs(pitch % 12 - pc + 12)))
                    pitch = (pitch // 12) * 12 + closest_diatonic_pc
                    while pitch < target_min_pitch: pitch += 12
                    while pitch > target_max_pitch: pitch -= 12
                    if pitch % 12 not in scale_note_pcs: pitch = None
                except ValueError: pitch = None

            if pitch is not None:
                melody_data.append((pitch, note_start_time_abs, actual_duration));
                last_melody_note = pitch

        current_abs_time_melody += duration_beats
        current_chord_idx += 1
    return melody_data


# --- Bass Line Generation Functions ---
def generate_bass_standard(progression_data, scale_notes): # Added scale_notes for potential future use
    """Generates standard bassline based on root notes and chord durations."""
    generated_bass_midi_data = []; start_time_beats = 0; bass_octave_shift = -24
    current_abs_time_bass = start_time_beats; min_bass = 28; max_bass = 60
    for bar_num, (_, _, _, chord_root_note, duration_beats) in enumerate(progression_data, 1): # Use duration_beats
        if chord_root_note is None or duration_beats <= 0: # Added duration check
            current_abs_time_bass += duration_beats if duration_beats > 0 else 1.0; continue

        bass_note_pitch = chord_root_note + bass_octave_shift
        while bass_note_pitch < min_bass: bass_note_pitch += 12
        while bass_note_pitch > max_bass: bass_note_pitch -= 12

        if duration_beats >= 0.1:
             note_start_time = current_abs_time_bass
             actual_duration = max(0.1, duration_beats * 0.9) # Hold slightly less than full duration
             generated_bass_midi_data.append((bass_note_pitch, note_start_time, actual_duration))

        current_abs_time_bass += duration_beats
    return generated_bass_midi_data

def generate_bass_walking(progression_data, scale_notes):
     """Generates a walking bass line respecting chord durations."""
     generated_bass_midi_data = []; start_time_beats = 0; bass_octave_shift = -24
     current_abs_time_bass = start_time_beats; last_bass_note = None
     min_bass = 28; max_bass = 60
     scale_note_pcs = {n % 12 for n in scale_notes} if scale_notes else set()
     if not scale_notes: print("Warning: Walking Bass generation cannot proceed without scale notes."); return []
     extended_bass_scale = sorted(list(set([n + oct_shift for n in scale_notes for oct_shift in [-36, -24, -12] if min_bass <= n + oct_shift <= max_bass + 7])))
     if not extended_bass_scale: extended_bass_scale = [n for n in range(min_bass, max_bass + 1) if n % 12 in scale_note_pcs] or [36, 38, 40, 41, 43, 45, 47]

     for bar_num, (chord_name, chord_notes_original, _, chord_root_note, duration_beats) in enumerate(progression_data, 1):
         if chord_root_note is None or not chord_notes_original or duration_beats <= 0: # Added duration check
             current_abs_time_bass += duration_beats if duration_beats > 0 else 1.0; continue

         target_root_pitch = chord_root_note + bass_octave_shift
         while target_root_pitch < min_bass: target_root_pitch += 12
         while target_root_pitch > max_bass: target_root_pitch -= 12
         closest_root_in_scale = min(extended_bass_scale, key=lambda x: abs(x - target_root_pitch))

         notes_for_chord_slot = []
         current_note_for_walk = closest_root_in_scale if last_bass_note is None else last_bass_note

         num_steps = int(duration_beats + 0.5)
         if num_steps <= 0:
             current_abs_time_bass += duration_beats; continue

         notes_for_chord_slot.append(closest_root_in_scale)
         current_note_for_walk = closest_root_in_scale

         for step in range(1, num_steps):
             possible_steps = get_stepwise_notes(current_note_for_walk, extended_bass_scale, max_step=2)

             if possible_steps:
                 next_note = random.choice(possible_steps)
                 if next_note == current_note_for_walk and len(possible_steps) > 1:
                     possible_steps.remove(next_note)
                     next_note = random.choice(possible_steps)

                 next_note = max(min_bass, min(max_bass, next_note))
                 notes_for_chord_slot.append(next_note)
                 current_note_for_walk = next_note
             else:
                 notes_for_chord_slot.append(current_note_for_walk) # Repeat last note

         beat_duration = 1.0 # Assume walking bass is quarter notes
         for i, pitch in enumerate(notes_for_chord_slot):
             note_start_time = current_abs_time_bass + (i * beat_duration)
             actual_duration = beat_duration * 0.95

             if note_start_time < current_abs_time_bass + duration_beats:
                 actual_duration = min(actual_duration, (current_abs_time_bass + duration_beats) - note_start_time)
                 if actual_duration > 0.01:
                      generated_bass_midi_data.append((pitch, note_start_time, actual_duration))
                      last_bass_note = pitch

         current_abs_time_bass += duration_beats
     return generated_bass_midi_data

# --- NEW Bass Style Functions (Basic Implementations) ---
def generate_bass_pop(progression_data, scale_notes):
    """Generates a simple Pop bassline (roots, maybe octaves)."""
    generated_bass_midi_data = []
    current_abs_time_bass = 0.0
    bass_octave_shift = -24
    min_bass = 28; max_bass = 60

    for _, _, _, chord_root_note, duration_beats in progression_data:
        if chord_root_note is None or duration_beats <= 0: # Added duration check
            current_abs_time_bass += duration_beats if duration_beats > 0 else 1.0; continue

        root_pitch = chord_root_note + bass_octave_shift
        while root_pitch < min_bass: root_pitch += 12
        while root_pitch > max_bass: root_pitch -= 12

        # Simple rhythm: quarter notes if possible
        num_beats = int(duration_beats + 0.5)
        for beat in range(num_beats):
            note_start = current_abs_time_bass + beat
            # Alternate root and octave sometimes?
            pitch = root_pitch
            if beat % 2 == 1 and duration_beats >= 2 and random.random() < 0.3:
                 pitch += 12
                 pitch = min(pitch, max_bass) # Keep octave within range

            if note_start < current_abs_time_bass + duration_beats:
                 actual_duration = min(1.0 * 0.9, (current_abs_time_bass + duration_beats) - note_start)
                 if actual_duration > 0.05:
                     generated_bass_midi_data.append((pitch, note_start, actual_duration))

        current_abs_time_bass += duration_beats
    return generated_bass_midi_data

def generate_bass_rnb(progression_data, scale_notes):
    """Generates a smoother RnB bassline (roots, fifths, simple rhythms)."""
    generated_bass_midi_data = []
    current_abs_time_bass = 0.0
    bass_octave_shift = -24
    min_bass = 28; max_bass = 65 # Allow slightly higher for RnB
    rhythms = [[(0, 0.75)], [(0, 0.5), (0.5, 0.5)], [(0, 0.75), (0.75, 0.25)], [(0, 1.5)]] # Simple 8th/dotted 8th feels

    for _, _, _, chord_root_note, duration_beats in progression_data:
        if chord_root_note is None or duration_beats <= 0: # Added duration check
            current_abs_time_bass += duration_beats if duration_beats > 0 else 1.0; continue

        root_pitch = chord_root_note + bass_octave_shift
        while root_pitch < min_bass: root_pitch += 12
        while root_pitch > max_bass: root_pitch -= 12
        fifth_pitch = root_pitch + 7
        if fifth_pitch > max_bass: fifth_pitch -= 12

        # Choose a rhythm pattern for the chord duration
        # This needs better adaptation to duration_beats
        chosen_rhythm = random.choice(rhythms)
        time_in_chord = 0
        for start_offset_beats, dur_beats in chosen_rhythm:
             note_start_abs = current_abs_time_bass + start_offset_beats
             # Select root or fifth
             pitch = root_pitch if random.random() < 0.7 else fifth_pitch

             actual_duration = min(dur_beats, duration_beats - start_offset_beats)
             if note_start_abs < current_abs_time_bass + duration_beats and actual_duration > 0.05:
                  generated_bass_midi_data.append((pitch, note_start_abs, actual_duration * 0.9)) # Slightly detach
             # This logic doesn't guarantee filling the duration_beats, needs refinement
             # For now, it just plays the pattern once at the start

        current_abs_time_bass += duration_beats
    return generated_bass_midi_data


def generate_bass_hip_hop(progression_data, scale_notes):
    """Generates a simple Hip Hop bassline (syncopated roots)."""
    generated_bass_midi_data = []
    current_abs_time_bass = 0.0
    bass_octave_shift = -24
    min_bass = 28; max_bass = 55 # Keep it lower typically
    # Simple syncopated patterns (start offset, duration in beats)
    rhythms = [ [(0, 0.75)], [(0.5, 0.75)], [(0, 0.4), (0.5, 0.4)], [(0.75, 0.75)] ]

    for _, _, _, chord_root_note, duration_beats in progression_data:
        if chord_root_note is None or duration_beats <= 0: # Added duration check
            current_abs_time_bass += duration_beats if duration_beats > 0 else 1.0; continue

        root_pitch = chord_root_note + bass_octave_shift
        while root_pitch < min_bass: root_pitch += 12
        while root_pitch > max_bass: root_pitch -= 12

        chosen_rhythm = random.choice(rhythms)
        for start_offset_beats, dur_beats in chosen_rhythm:
            note_start_abs = current_abs_time_bass + start_offset_beats
            actual_duration = min(dur_beats * 0.9, duration_beats - start_offset_beats) # Detached

            if note_start_abs < current_abs_time_bass + duration_beats and actual_duration > 0.05:
                 generated_bass_midi_data.append((root_pitch, note_start_abs, actual_duration))

        current_abs_time_bass += duration_beats
    return generated_bass_midi_data

def generate_bass_808(progression_data, scale_notes):
    """Generates a simple 808 bassline (long roots, lower octave)."""
    generated_bass_midi_data = []
    current_abs_time_bass = 0.0
    bass_octave_shift = -36 # Lower for 808s
    min_bass = 20; max_bass = 48 # Very low range

    for _, _, _, chord_root_note, duration_beats in progression_data:
        if chord_root_note is None or duration_beats <= 0: # Added duration check
            current_abs_time_bass += duration_beats if duration_beats > 0 else 1.0; continue

        root_pitch = chord_root_note + bass_octave_shift
        while root_pitch < min_bass: root_pitch += 12
        # Don't force down if it's already low
        # while root_pitch > max_bass: root_pitch -= 12
        root_pitch = max(min_bass, min(root_pitch, max_bass)) # Clamp


        # Usually long notes, maybe slight variation
        note_start_time = current_abs_time_bass
        actual_duration = max(0.5, duration_beats * 0.98) # Long sustain

        # Simple rhythm - just the root note for the duration
        generated_bass_midi_data.append((root_pitch, note_start_time, actual_duration))

        # Optional: Add occasional short note or slide (more complex)

        current_abs_time_bass += duration_beats
    return generated_bass_midi_data


# --- Custom Label for Drag and Drop ---
class DragMidiLabel(QLabel):
    """ A QLabel subclass that initiates a drag operation for a MIDI file. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.midi_file_path = None
        self.drag_start_position = QPoint()
        self.setToolTip("Click and drag the saved MIDI file from here") # Tooltip set here
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        # Set initial text (stylesheet handles boldness/styling)
        self.setText("(Generate MIDI first)")
        self.setObjectName("DragMidiLabel") # Keep ID for styling
        # Store original tooltip
        self.setProperty("originalToolTip", "Click and drag the saved MIDI file from here")

    def set_midi_path(self, file_path):
        """ Sets the path of the MIDI file that can be dragged. """
        self.midi_file_path = file_path
        if file_path and os.path.exists(file_path):
            filename = os.path.basename(file_path)
            self.setText(f"Drag: {filename}")
            new_tooltip = f"Drag {filename} to your DAW"
            self.setProperty("originalToolTip", new_tooltip) # Update stored tooltip
            # Update visible tooltip based on global setting
            if self.window() and hasattr(self.window(), 'show_tooltips') and self.window().show_tooltips:
                self.setToolTip(new_tooltip)
            else:
                self.setToolTip("")
        else:
            self.midi_file_path = None
            self.setText("(Generate MIDI first)")
            new_tooltip = "Click and drag the saved MIDI file from here"
            self.setProperty("originalToolTip", new_tooltip) # Reset stored tooltip
            # Update visible tooltip based on global setting
            if self.window() and hasattr(self.window(), 'show_tooltips') and self.window().show_tooltips:
                 self.setToolTip(new_tooltip)
            else:
                self.setToolTip("")

    def mousePressEvent(self, event):
        """ Stores the starting position of the mouse press. """
        if event.button() == Qt.MouseButton.LeftButton and self.midi_file_path:
            self.drag_start_position = event.position().toPoint()
        else:
            self.drag_start_position = QPoint()
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """ Initiates the drag operation if the mouse moves sufficiently. """
        if not (event.buttons() & Qt.MouseButton.LeftButton): return
        if not self.midi_file_path or not os.path.exists(self.midi_file_path): return
        if self.drag_start_position.isNull(): return
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self); mime_data = QMimeData()
        file_url = QUrl.fromLocalFile(self.midi_file_path)
        mime_data.setUrls([file_url])
        drag.setMimeData(mime_data)
        # --- NO PIXMAP SET --- (Intentionally kept)
        drop_action = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

# --- NEW: Simple Piano Roll Widget ---
class PianoRollWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120) # Set a default minimum height
        self.chords_data = []
        self.arp_data = []
        self.bass_data = []
        self.melody_data = []
        self.total_beats = 16.0 # Default
        self.min_pitch = 36 # C2
        self.max_pitch = 96 # C7
        self.pitch_span = self.max_pitch - self.min_pitch + 1

        # Define colors for different tracks
        self.chord_color = QColor(100, 100, 255, 180) # Blueish
        self.bass_color = QColor(255, 100, 100, 180) # Reddish
        self.arp_color = QColor(100, 255, 100, 180) # Greenish
        self.melody_color = QColor(255, 165, 0, 200) # Orange
        # Grid colors are now set in paintEvent based on theme

        # --- ADDED TOOLTIP ---
        tooltip_text = ("Color Legend:\n"
                        "- Blue: Chords\n"
                        "- Red: Bassline\n"
                        "- Green: Arpeggio\n"
                        "- Orange: Melody")
        self.setProperty("originalToolTip", tooltip_text) # Store it
        # Set initial visibility based on parent window's state (if available)
        if parent and hasattr(parent, 'show_tooltips') and parent.show_tooltips:
            self.setToolTip(tooltip_text)
        else:
            self.setToolTip("") # Initially hidden if parent says so or no parent context yet

    def set_data(self, chords, arp, bass, melody, total_beats):
        self.chords_data = chords if chords else []
        self.arp_data = arp if arp else []
        self.bass_data = bass if bass else []
        self.melody_data = melody if melody else []
        self.total_beats = max(1.0, total_beats) # Ensure at least 1 beat
        self.update() # Trigger repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        widget_rect = self.rect()
        # Get theme colors
        bg_color = self.palette().color(QPalette.ColorRole.Base)
        grid_color = self.palette().color(QPalette.ColorRole.AlternateBase).darker(110) # Use a darker version of alternate base for grid
        beat_color = grid_color.darker(120)
        bar_color = grid_color.darker(150)

        painter.fillRect(widget_rect, bg_color)

        w = widget_rect.width()
        h = widget_rect.height()

        if w <= 0 or h <= 0 or self.pitch_span <= 0 or self.total_beats <= 0:
            return # Nothing to draw

        # --- Draw Grid Lines ---
        note_height = max(1.0, h / self.pitch_span) # Min height of 1 pixel

        # Horizontal lines (pitch) - Draw faint lines for each pitch
        painter.setPen(grid_color)
        for i in range(self.pitch_span):
            y = h - (i * note_height) # Draw line at the *top* of the note rectangle area
            painter.drawLine(0, int(y), w, int(y))

        # Vertical lines (time)
        beats_per_bar = 4.0
        num_bars = math.ceil(self.total_beats / beats_per_bar)

        for beat in range(int(self.total_beats) + 1):
            x = w * (beat / self.total_beats)
            is_bar_line = (beat % beats_per_bar == 0)
            painter.setPen(bar_color if is_bar_line else beat_color)
            painter.drawLine(int(x), 0, int(x), h)

        # --- Draw Notes ---
        note_pen = QPen(Qt.PenStyle.NoPen) # No border for notes generally

        # Helper to draw notes for a track
        def draw_notes(notes_list, color, is_chord=False):
            painter.setBrush(QBrush(color))
            painter.setPen(note_pen)

            current_chord_start_time = 0 # Only used for is_chord=True

            for index, note_info in enumerate(notes_list):
                if is_chord:
                    # chords_data = (display_name, original_notes, midi_notes, root_note, duration_beats)
                    # Use the pre-calculated start time for this chord
                    start_time = current_chord_start_time
                    pitches = note_info[2] # midi_notes
                    duration = note_info[4]
                    # Update start time for the *next* chord
                    current_chord_start_time += duration

                    if not pitches or duration <= 0: continue
                    for pitch in pitches:
                         if self.min_pitch <= pitch <= self.max_pitch:
                            y = h - ((pitch - self.min_pitch + 1) * note_height) # Top edge of note
                            x = w * (start_time / self.total_beats)
                            rect_w = w * (duration / self.total_beats)
                            # Use QRectF for precision, ensure minimum visible size
                            # <<<<<<<<<<<<<<<<<<<<<<<<<<<<< MODIFICATION >>>>>>>>>>>>>>>>>>>>>>>>>>>>
                            # Removed the "- 0.2" gap for width and height
                            note_rect = QRectF(x, y, max(1.5, rect_w), max(1.0, note_height))
                            # <<<<<<<<<<<<<<<<<<<<<<<<<<<<< END MODIFICATION >>>>>>>>>>>>>>>>>>>>>>>>>
                            painter.drawRect(note_rect)
                else:
                    # arp_data = (pitch, start_time, duration, velocity)
                    # bass/melody_data = (pitch, start_time, duration)
                    pitch = note_info[0]
                    start_time = note_info[1]
                    duration = note_info[2]

                    if self.min_pitch <= pitch <= self.max_pitch and duration > 0:
                        y = h - ((pitch - self.min_pitch + 1) * note_height) # Top edge of note
                        x = w * (start_time / self.total_beats)
                        rect_w = w * (duration / self.total_beats)
                        # Use QRectF for precision, ensure minimum visible size
                        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<< MODIFICATION >>>>>>>>>>>>>>>>>>>>>>>>>>>>
                        # Removed the "- 0.2" gap for width and height
                        note_rect = QRectF(x, y, max(1.5, rect_w), max(1.0, note_height))
                        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<< END MODIFICATION >>>>>>>>>>>>>>>>>>>>>>>>>
                        painter.drawRect(note_rect)

        # Draw tracks (order matters for overlap visibility - draw chords first)
        if self.chords_data: draw_notes(self.chords_data, self.chord_color, is_chord=True)
        if self.bass_data: draw_notes(self.bass_data, self.bass_color)
        if self.arp_data: draw_notes(self.arp_data, self.arp_color)
        if self.melody_data: draw_notes(self.melody_data, self.melody_color)


# --- PyQt6 GUI Class ---
class ChorgiWindow(QWidget):
    def __init__(self):
        super().__init__()
        # --- Instance variables ---
        self.show_tooltips = True # <-- Added state for tooltip visibility
        self.generated_chords_progression = []
        self.generated_arp_midi_data = []
        self.generated_bass_midi_data = []
        self.generated_melody_midi_data = []
        self.last_generated_key = ""
        self.last_generated_key_type = "major" # Default, overwritten
        self.last_generated_num_bars = 12 # Default
        # self.last_chord_rhythm_selection = "Block" # Removed
        self.last_complexity_selection = "Standard (Triads/7ths)"
        self.last_style_selection = "Chorgi"
        self.last_generated_filename_base = ""
        self.last_saved_midi_path = None
        self.save_directory = None
        self.generation_count = 0
        self.include_arp = True
        self.include_melody = True
        self.include_bass = True
        self.last_blues_pattern_index = -1 # Initialize to -1 (no pattern used yet)

        # --- Theme Palettes and Stylesheets ---
        self._define_themes()

        # --- UI Initialization ---
        self.initUI()
        self._get_save_directory() # Try to get save dir on init
        self._apply_theme("Dark (Nord)") # Apply default theme


    def _define_themes(self):
        """Defines the palettes and stylesheets for different themes."""
        # --- Dark (Nord) Palette --- (Using tooltip colors)
        self.dark_palette = QPalette()
        BG_COLOR_D = QColor("#2E3440") # Nord Polar Night bg
        FG_COLOR_D = QColor("#ECEFF4") # Nord Snow Storm fg
        BTN_COLOR_D = QColor("#4C566A") # Nord Polar Night lighter bg for buttons
        BTN_TEXT_COLOR_D = QColor("#ECEFF4")
        HIGHLIGHT_COLOR_D = QColor("#88C0D0") # Nord Frost highlight
        BORDER_COLOR_D = QColor("#434C5E")
        SOFT_TEXT_COLOR_D = QColor("#D8DEE9")
        DISABLED_FG_D = QColor("#6c7a94")
        DISABLED_BG_D = QColor("#434C5E")
        BASE_COLOR_D = QColor("#3B4252") # Slightly lighter base
        ALERT_COLOR_D = QColor("#BF616A") # Nord Frost red for alerts
        TOOLTIP_BG_D = QColor("#4C566A") # Use a distinct tooltip bg
        TOOLTIP_FG_D = QColor("#ECEFF4") # Use bright text for tooltip

        self.dark_palette.setColor(QPalette.ColorRole.Window, BG_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.WindowText, FG_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.Base, BASE_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.AlternateBase, BTN_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.ToolTipBase, TOOLTIP_BG_D) # Set tooltip background
        self.dark_palette.setColor(QPalette.ColorRole.ToolTipText, TOOLTIP_FG_D) # Set tooltip text
        self.dark_palette.setColor(QPalette.ColorRole.Text, SOFT_TEXT_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.Button, BTN_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.ButtonText, BTN_TEXT_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.BrightText, ALERT_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.Link, HIGHLIGHT_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.Highlight, HIGHLIGHT_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorRole.HighlightedText, BG_COLOR_D)
        self.dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, DISABLED_FG_D)
        self.dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, DISABLED_FG_D)
        self.dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, DISABLED_FG_D)
        self.dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, DISABLED_BG_D)
        self.dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, DISABLED_BG_D)

        # --- Light (Grey) Palette --- (Using tooltip colors)
        self.light_palette = QPalette()
        BG_COLOR_L = QColor("#DCDCDC") # Gainsboro grey bg
        FG_COLOR_L = QColor("#2E3440") # Dark theme bg as text color
        BTN_COLOR_L = QColor("#C8C8C8") # Slightly darker grey buttons
        BTN_TEXT_COLOR_L = QColor("#2E3440") # Darker text for buttons
        HIGHLIGHT_COLOR_L = QColor("#007ACC") # Standard blue highlight
        BORDER_COLOR_L = QColor("#B0B0B0") # Darker grey border
        SOFT_TEXT_COLOR_L = QColor("#3B4252") # Dark theme base as softer text
        DISABLED_FG_L = QColor("#888888") # Lighter grey for disabled text
        DISABLED_BG_L = QColor("#E8E8E8") # Light grey disabled bg
        BASE_COLOR_L = QColor("#F0F0F0") # Slightly lighter base for inputs
        ALERT_COLOR_L = QColor("#C62828") # Slightly darker red
        TOOLTIP_BG_L = QColor("#FFFFE1") # Standard light yellow tooltip bg
        TOOLTIP_FG_L = QColor("#000000") # Standard black tooltip text

        self.light_palette.setColor(QPalette.ColorRole.Window, BG_COLOR_L)
        self.light_palette.setColor(QPalette.ColorRole.WindowText, FG_COLOR_L)
        self.light_palette.setColor(QPalette.ColorRole.Base, BASE_COLOR_L) # Input background
        self.light_palette.setColor(QPalette.ColorRole.AlternateBase, BTN_COLOR_L)
        self.light_palette.setColor(QPalette.ColorRole.ToolTipBase, TOOLTIP_BG_L) # Set tooltip background
        self.light_palette.setColor(QPalette.ColorRole.ToolTipText, TOOLTIP_FG_L) # Set tooltip text
        self.light_palette.setColor(QPalette.ColorRole.Text, SOFT_TEXT_COLOR_L) # General text on bg
        self.light_palette.setColor(QPalette.ColorRole.Button, BTN_COLOR_L)
        self.light_palette.setColor(QPalette.ColorRole.ButtonText, BTN_TEXT_COLOR_L)
        self.light_palette.setColor(QPalette.ColorRole.BrightText, ALERT_COLOR_L)
        self.light_palette.setColor(QPalette.ColorRole.Link, HIGHLIGHT_COLOR_L)
        self.light_palette.setColor(QPalette.ColorRole.Highlight, HIGHLIGHT_COLOR_L)
        self.light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF")) # White text on blue highlight
        self.light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, DISABLED_FG_L)
        self.light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, DISABLED_FG_L)
        self.light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, DISABLED_FG_L)
        self.light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, DISABLED_BG_L)
        self.light_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, DISABLED_BG_L)


        # --- Dark (Nord) Stylesheet ---
        # --- FIX: Reinstated MINIMAL QToolTip styling with rounded corners ---
        self.dark_stylesheet = f"""
            QWidget {{
                font-family: Segoe UI, Arial, sans-serif; font-size: 10pt;
                color: #ECEFF4; /* FG_COLOR_D */
                background-color: #2E3440; /* BG_COLOR_D */
            }}
            QToolTip {{
                color: #ECEFF4; /* TOOLTIP_FG_D */
                background-color: #4C566A; /* TOOLTIP_BG_D */
                border: 1px solid #434C5E; /* Simple border matching theme */
                padding: 4px; /* Slightly more padding */
                border-radius: 4px; /* Rounded corners */
            }}
            QGroupBox {{
                background-color: #3B4252; /* BASE_COLOR_D */
                border: 1px solid #434C5E; /* BORDER_COLOR_D */
                border-radius: 5px;
                margin-top: 10px; /* Space for title */
                padding: 10px 5px 5px 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                margin-left: 10px;
                background-color: #3B4252; /* BASE_COLOR_D */
                color: #88C0D0; /* HIGHLIGHT_COLOR_D */
                font-weight: bold;
            }}
            QLabel {{ /* General Labels - BOLD */
                color: #D8DEE9; padding-bottom: 2px; background-color: transparent;
                font-weight: bold;
            }}
            QLabel#SectionLabel {{ /* Already Bold */
                color: #ECEFF4; margin-top: 5px; margin-bottom: 2px; background-color: transparent;
            }}
            QLabel#ChordDisplayLabel {{ /* Progression Display - BOLD */
                color: #A3BE8C; /* Nord Frost green */
                background-color: #434C5E;
                border: 1px solid #4C566A;
                border-radius: 4px; padding: 5px;
                font-family: Consolas, Courier New, monospace; font-size: 9pt;
                min-height: 35px;
                font-weight: bold; /* MODIFIED */
            }}
             QLabel#BrandingLabel {{ /* Keep Normal Weight */
                font-size: 10pt; color: #6c7a94;
                font-weight: normal; padding-top: 2px; background-color: transparent;
            }}
            QLabel#DragMidiLabel {{ /* Drag MIDI Label - BOLD and Smaller */
                 border: 2px dashed #4C566A; background-color: #3B4252; color: #A3BE8C;
                 padding: 5px; border-radius: 5px; min-height: 35px; /* MODIFIED padding, min-height */
                 font-size: 9pt;
                 font-weight: bold; /* MODIFIED */
            }}
             #DragMidiLabel:hover {{ border-color: #5E81AC; color: #B48EAD; }}
             /* Remove specific bold style for <b> tag inside DragMidiLabel if main label is bold */
             /* #DragMidiLabel > b {{ font-weight: bold; color: #ECEFF4; }} */

            QComboBox {{ /* Bold Text */
                background-color: #434C5E; color: #ECEFF4;
                border: 1px solid #4C566A; padding: 5px 8px;
                min-height: 22px; border-radius: 4px;
                font-weight: bold;
            }}
            QComboBox:hover {{ background-color: #4C566A; border: 1px solid #5E81AC; }}
            QComboBox::drop-down {{ border: none; background-color: transparent; width: 15px; padding-right: 5px; }}
            QComboBox::down-arrow {{ image: url(:/qt-project.org/styles/commonstyle/images/downarraow-16.png); width: 12px; height: 12px; }}
            QComboBox QAbstractItemView {{ /* Dropdown list items - Normal Weight */
                background-color: #3B4252; color: #ECEFF4;
                selection-background-color: #88C0D0; selection-color: #2E3440;
                border: 1px solid #4C566A; padding: 3px; outline: 0px;
                border-radius: 4px; margin-top: 2px;
                font-weight: normal;
            }}
            QComboBox:disabled {{ background-color: #434C5E; color: #6c7a94; border: 1px solid #434C5E; }}

            QSpinBox {{ /* Bold Text */
                background-color: #434C5E; color: #ECEFF4;
                border: 1px solid #4C566A; padding: 4px 6px;
                min-height: 22px; border-radius: 4px;
                font-weight: bold;
            }}
            QSpinBox:hover {{ background-color: #4C566A; border: 1px solid #5E81AC; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border; background-color: #4C566A;
                border: none; width: 16px; border-radius: 2px;
            }}
            QSpinBox::up-button {{ subcontrol-position: top right; margin: 2px; }}
            QSpinBox::down-button {{ subcontrol-position: bottom right; margin: 2px; }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: #5E81AC; }}
            QSpinBox::up-arrow {{ image: url(:/qt-project.org/styles/commonstyle/images/uparrow-16.png); width: 10px; height: 10px; }}
            QSpinBox::down-arrow {{ image: url(:/qt-project.org/styles/commonstyle/images/downarrow-16.png); width: 10px; height: 10px; }}
            QSpinBox:disabled {{ background-color: #434C5E; color: #6c7a94; border: 1px solid #434C5E; }}
            QSpinBox::up-button:disabled, QSpinBox::down-button:disabled {{ background-color: #3B4252; }}

            QPushButton {{ /* Buttons Remain Bold */
                background-color: #5E81AC; color: #ECEFF4; border: none;
                padding: 8px 18px; border-radius: 4px; font-weight: bold; min-height: 26px;
            }}
            QPushButton:hover {{ background-color: #81A1C1; }}
            QPushButton#GenerateButton:pressed {{
                background-color: #506d91; padding-top: 10px; padding-bottom: 6px;
            }}
            QPushButton:disabled {{ background-color: #434C5E; color: #6c7a94; }}
            QPushButton#RandomizeButton {{ background-color: #4C566A; font-size: 14pt; padding: 5px 10px; min-height: 20px; }}
            QPushButton#RandomizeButton:hover {{ background-color: #5E81AC; }}
            QPushButton#RandomizeButton:pressed {{ background-color: #3B4252; }}
            QPushButton#RegenerateButton {{ background-color: #4C566A; }}
            QPushButton#RegenerateButton:hover {{ background-color: #5a6780; }}
            QPushButton#RegenerateButton:pressed {{ background-color: #434C5E; }}
            QPushButton#SupportButton {{ /* Keep Normal */
                background-color: #434C5E; color: #D8DEE9; font-size: 8pt;
                font-weight: normal; padding: 3px 8px; min-height: 18px; max-width: 60px;
            }}
             QPushButton#SupportButton:hover {{ background-color: #4C566A; }}
             QPushButton#SupportButton:pressed {{ background-color: #3B4252; }}

            QCheckBox {{ /* Bold Text */
                spacing: 8px; color: #D8DEE9; background-color: transparent;
                font-weight: bold;
            }}
            QCheckBox#EmbedTempoCheck {{ font-size: 9pt; font-weight: bold; }} /* Ensure tempo checkbox is bold too */
            QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid #4C566A; border-radius: 3px; background-color: #3B4252; }}
            QCheckBox::indicator:hover {{ border: 1px solid #5E81AC; }}
            QCheckBox::indicator:checked {{ background-color: #88C0D0; border: 1px solid #88C0D0; }}
            QCheckBox::indicator:checked:hover {{ background-color: #96cddb; border: 1px solid #96cddb; }}
            QCheckBox:disabled {{ color: #6c7a94; }}
            QCheckBox::indicator:disabled {{ border-color: #434C5E; background-color: #3B4252; }}

            QRadioButton {{ /* Bold Text */
                spacing: 5px; color: #D8DEE9; background-color: transparent;
                font-weight: bold;
            }}
            /* --- MODIFIED: Make RadioButton indicator square --- */
            QRadioButton::indicator {{
                width: 14px; height: 14px;
                border: 1px solid #4C566A;
                border-radius: 3px; /* Make it square like checkbox */
                background-color: #3B4252;
            }}
            QRadioButton::indicator:hover {{ border: 1px solid #5E81AC; }}
            /* --- MODIFIED: Make checked state a solid fill --- */
            QRadioButton::indicator:checked {{
                background-color: #88C0D0; /* Use CheckBox checked color */
                border: 1px solid #88C0D0;
            }}
            QRadioButton::indicator:checked:hover {{ background-color: #96cddb; border: 1px solid #96cddb; }}
            QRadioButton:disabled {{ color: #6c7a94; }}
            QRadioButton::indicator:disabled {{
                border-color: #434C5E; background-color: #3B4252;
            }}
            QRadioButton::indicator:checked:disabled {{
                 background-color: #6c7a94; /* Use disabled check color */
                 border: 1px solid #434C5E;
            }}
        """

        # --- Light (Grey) Stylesheet ---
        # --- FIX: Reinstated MINIMAL QToolTip styling with rounded corners ---
        self.light_stylesheet = f"""
            QWidget {{
                font-family: Segoe UI, Arial, sans-serif; font-size: 10pt;
                color: #2E3440; /* FG_COLOR_L - Dark Text */
                background-color: #DCDCDC; /* BG_COLOR_L - Grey BG */
            }}
            QToolTip {{
                color: #000000; /* TOOLTIP_FG_L */
                background-color: #FFFFE1; /* TOOLTIP_BG_L */
                border: 1px solid #B0B0B0; /* Simple border */
                padding: 4px; /* Slightly more padding */
                border-radius: 4px; /* Rounded corners */
            }}
            QGroupBox {{
                background-color: #F0F0F0; /* BASE_COLOR_L - Lighter BG for contrast */
                border: 1px solid #B0B0B0; /* BORDER_COLOR_L */
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px 5px 5px 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                margin-left: 10px;
                background-color: #F0F0F0; /* Match GroupBox BG */
                color: #005A9E; /* Dark Blue title */
                font-weight: bold;
            }}
            QLabel {{ /* General Labels - BOLD */
                color: #3B4252; padding-bottom: 2px; background-color: transparent;
                font-weight: bold;
            }}
            QLabel#SectionLabel {{ /* Already Bold */
                 color: #2E3440; margin-top: 5px; margin-bottom: 2px; background-color: transparent;
            }}
            QLabel#ChordDisplayLabel {{ /* Progression Display - BOLD */
                color: #005A9E; /* Dark Blue Text */
                background-color: #E8E8E8;
                border: 1px solid #B0B0B0;
                border-radius: 4px; padding: 5px;
                font-family: Consolas, Courier New, monospace; font-size: 9pt;
                min-height: 35px;
                font-weight: bold; /* MODIFIED */
            }}
             QLabel#BrandingLabel {{ /* Keep Normal Weight */
                font-size: 10pt; color: #505050;
                font-weight: normal; padding-top: 2px; background-color: transparent;
            }}
             QLabel#DragMidiLabel {{ /* Drag MIDI Label - BOLD and Smaller */
                 border: 2px dashed #A0A0A0; background-color: #E8E8E8; color: #005A9E;
                 padding: 5px; border-radius: 5px; min-height: 35px; /* MODIFIED padding, min-height */
                 font-size: 9pt;
                 font-weight: bold; /* MODIFIED */
            }}
             #DragMidiLabel:hover {{ border-color: #007ACC; color: #004C80; }}
             /* Remove specific bold style for <b> tag inside DragMidiLabel if main label is bold */
             /* #DragMidiLabel > b {{ font-weight: bold; color: #004C80; }} */

            QComboBox {{ /* Bold Text */
                background-color: #FFFFFF; color: #2E3440; /* White BG, Dark Text */
                border: 1px solid #B0B0B0; padding: 5px 8px;
                min-height: 22px; border-radius: 4px;
                font-weight: bold;
            }}
            QComboBox:hover {{ border: 1px solid #007ACC; }}
            QComboBox::drop-down {{ border: none; background-color: transparent; width: 15px; padding-right: 5px; }}
            QComboBox::down-arrow {{ image: url(:/qt-project.org/styles/commonstyle/images/downarraow-16.png); width: 12px; height: 12px; }}
            QComboBox QAbstractItemView {{ /* Dropdown list items - Normal Weight */
                background-color: #FFFFFF; color: #2E3440;
                selection-background-color: #007ACC; selection-color: #FFFFFF;
                border: 1px solid #B0B0B0; padding: 3px; outline: 0px;
                border-radius: 4px; margin-top: 2px;
                font-weight: normal;
            }}
            QComboBox:disabled {{ background-color: #E8E8E8; color: #888888; border: 1px solid #C8C8C8; }}

            QSpinBox {{ /* Bold Text */
                background-color: #FFFFFF; color: #2E3440; /* White BG, Dark Text */
                border: 1px solid #B0B0B0; padding: 4px 6px;
                min-height: 22px; border-radius: 4px;
                font-weight: bold;
            }}
            QSpinBox:hover {{ border: 1px solid #007ACC; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border; background-color: #E0E0E0; /* Grey buttons */
                border: 1px solid #B0B0B0; width: 16px; border-radius: 2px;
            }}
            QSpinBox::up-button {{ subcontrol-position: top right; margin: 2px; }}
            QSpinBox::down-button {{ subcontrol-position: bottom right; margin: 2px; }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: #C8E6FC; border-color: #007ACC; }}
            QSpinBox::up-arrow {{ image: url(:/qt-project.org/styles/commonstyle/images/uparrow-16.png); width: 10px; height: 10px; }}
            QSpinBox::down-arrow {{ image: url(:/qt-project.org/styles/commonstyle/images/downarrow-16.png); width: 10px; height: 10px; }}
            QSpinBox:disabled {{ background-color: #E8E8E8; color: #888888; border: 1px solid #C8C8C8; }}
            QSpinBox::up-button:disabled, QSpinBox::down-button:disabled {{ background-color: #F0F0F0; border-color: #C8C8C8; }}

            QPushButton {{ /* Buttons Remain Bold */
                background-color: #007ACC; color: #FFFFFF; border: none;
                padding: 8px 18px; border-radius: 4px; font-weight: bold; min-height: 26px;
            }}
            QPushButton:hover {{ background-color: #005A9E; }}
            QPushButton#GenerateButton:pressed {{
                background-color: #004C80; padding-top: 10px; padding-bottom: 6px;
            }}
            QPushButton:disabled {{ background-color: #E0E0E0; color: #888888; }}
            QPushButton#RandomizeButton {{ background-color: #C8C8C8; color: #2E3440; font-size: 14pt; padding: 5px 10px; min-height: 20px; }}
            QPushButton#RandomizeButton:hover {{ background-color: #B8B8B8; border: 1px solid #A0A0A0;}}
            QPushButton#RandomizeButton:pressed {{ background-color: #A8A8A8; }}
            QPushButton#RegenerateButton {{ background-color: #D0D0D0; color: #2E3440;}}
            QPushButton#RegenerateButton:hover {{ background-color: #C0C0C0; border: 1px solid #A0A0A0;}}
            QPushButton#RegenerateButton:pressed {{ background-color: #B0B0B0; }}
            QPushButton#SupportButton {{ /* Keep Normal */
                background-color: #E0E0E0; color: #3B4252; font-size: 8pt;
                font-weight: normal; padding: 3px 8px; min-height: 18px; max-width: 60px; border: 1px solid #B8B8B8;
            }}
             QPushButton#SupportButton:hover {{ background-color: #D0D0D0; border-color: #A8A8A8; }}
             QPushButton#SupportButton:pressed {{ background-color: #C0C0C0; }}

            QCheckBox {{ /* Bold Text */
                spacing: 8px; color: #3B4252; background-color: transparent;
                font-weight: bold;
            }}
            QCheckBox#EmbedTempoCheck {{ font-size: 9pt; font-weight: bold; }} /* Ensure tempo checkbox is bold too */
            QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid #A0A0A0; border-radius: 3px; background-color: #FFFFFF; }}
            QCheckBox::indicator:hover {{ border: 1px solid #007ACC; }}
            QCheckBox::indicator:checked {{ background-color: #007ACC; border: 1px solid #005A9E; }}
            QCheckBox::indicator:checked:hover {{ background-color: #005A9E; }}
            QCheckBox:disabled {{ color: #888888; }}
            QCheckBox::indicator:disabled {{ border-color: #C8C8C8; background-color: #F0F0F0; }}

            QRadioButton {{ /* Bold Text */
                spacing: 5px; color: #3B4252; background-color: transparent;
                font-weight: bold;
            }}
            /* --- MODIFIED: Make RadioButton indicator square --- */
            QRadioButton::indicator {{
                width: 14px; height: 14px;
                border: 1px solid #A0A0A0;
                border-radius: 3px; /* Make it square like checkbox */
                background-color: #FFFFFF;
            }}
            QRadioButton::indicator:hover {{ border: 1px solid #007ACC; }}
            /* --- MODIFIED: Make checked state a solid fill --- */
            QRadioButton::indicator:checked {{
                background-color: #007ACC; /* Use CheckBox checked color */
                border: 1px solid #005A9E;
            }}
             QRadioButton::indicator:checked:hover {{ background-color: #005A9E; }}
            QRadioButton:disabled {{ color: #888888; }}
            QRadioButton::indicator:disabled {{
                border-color: #C8C8C8; background-color: #F0F0F0;
            }}
            QRadioButton::indicator:checked:disabled {{
                background-color: #B0B0B0; /* Use disabled check color */
                border: 1px solid #C8C8C8;
             }}
        """

    def _get_save_directory(self):
        """Gets the dedicated save directory path, creating it if necessary."""
        # (Function remains the same)
        try:
            docs_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
            if not docs_path: # If DocumentsLocation is empty
                docs_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation)
            if not docs_path: # If HomeLocation is also empty (unlikely)
                 docs_path = os.path.expanduser("~") # Final fallback for home

            if not docs_path or not os.path.isdir(docs_path):
                 self.save_directory = "."
                 if QApplication.instance():
                      self.show_error_message("Save Directory Error", "Could not find Documents or Home directory.\nSaving MIDI files to the application's current directory.")
                 return False

            self.save_directory = os.path.join(docs_path, "Chorgi MIDI Files")
            os.makedirs(self.save_directory, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error determining or creating save directory: {e}")
            self.save_directory = "."
            if QApplication.instance():
                 self.show_error_message("Save Directory Error", f"Could not create save directory:\n{e}\nSaving to current directory.")
            return False


    def initUI(self):
        """Sets up the user interface with refactored controls."""
        # --- Fonts --- (Simplified, rely more on stylesheet)
        self.button_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.status_font = QFont("Segoe UI", 11)
        self.footer_font = QFont("Segoe UI", 10, QFont.Weight.Normal)
        self.tempo_label_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.group_box_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self.tooltip_toggle_font = QFont("Segoe UI", 9) # Font for tooltip toggle

        self.setWindowTitle("Chorgi")
        self.resize(750, 850) # Adjusted size for piano roll
        self.setAutoFillBackground(True)

        # --- Main Layout (Vertical) ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # --- Tooltip Toggle Layout (Top Right) ---
        tooltip_layout = QHBoxLayout()
        tooltip_layout.addStretch(1) # Push checkbox to the right
        self.tooltip_checkbox = QCheckBox("Show Tooltips")
        self.tooltip_checkbox.setFont(self.tooltip_toggle_font)
        self.tooltip_checkbox.setChecked(self.show_tooltips)
        tooltip_text = "Enable or disable all informational tooltips"
        self.tooltip_checkbox.setProperty("originalToolTip", tooltip_text) # Store original
        self.tooltip_checkbox.setToolTip(tooltip_text if self.show_tooltips else "") # Set initial
        self.tooltip_checkbox.stateChanged.connect(self._toggle_tooltips_slot)
        tooltip_layout.addWidget(self.tooltip_checkbox)
        self.main_layout.addLayout(tooltip_layout) # Add to main layout *first*
        self.main_layout.addSpacing(5) # Add a little space

        # --- Horizontal Layout for the two main columns of controls ---
        self.columns_layout = QHBoxLayout()
        self.columns_layout.setSpacing(15)

        # --- Column 1 Layout (Vertical) ---
        column1_layout = QVBoxLayout()
        column1_layout.setSpacing(10)

        # Style, Key, Bars, Complexity, Tempo Group (Column 1)
        general_group = QGroupBox("General Settings")
        general_group.setFont(self.group_box_font)
        general_layout = QVBoxLayout(general_group)
        general_layout.setSpacing(8)
        general_layout.addLayout(self.create_style_key_controls()) # Style (Pool), Key, Type
        general_layout.addLayout(self.create_structure_controls()) # Bars, Complexity, BPM
        column1_layout.addWidget(general_group)

        # --- NEW: Progression Settings Group (Column 1) ---
        prog_group = QGroupBox("Progression Settings")
        prog_group.setFont(self.group_box_font)
        prog_group.setLayout(self.create_progression_controls())
        column1_layout.addWidget(prog_group)

        # Chords Group (Bias Only Now) (Column 1)
        chords_group = QGroupBox("Chord Settings")
        chords_group.setFont(self.group_box_font)
        chords_layout = QVBoxLayout(chords_group)
        chords_layout.setSpacing(8)
        chords_layout.addLayout(self.create_chord_bias_control())
        column1_layout.addWidget(chords_group)

        # Arpeggiator Group (Column 1)
        arp_group = QGroupBox("Arpeggiator Settings")
        arp_group.setFont(self.group_box_font)
        arp_layout = QVBoxLayout(arp_group)
        arp_layout.setSpacing(8)
        arp_layout.addLayout(self.create_arp_controls())
        column1_layout.addWidget(arp_group)

        column1_layout.addStretch(1)
        self.columns_layout.addLayout(column1_layout, 1)

        # --- Column 2 Layout (Vertical) ---
        column2_layout = QVBoxLayout()
        column2_layout.setSpacing(10)

        # Melody Group (Column 2)
        melody_group = QGroupBox("Melody Settings")
        melody_group.setFont(self.group_box_font)
        melody_group.setLayout(self.create_melody_controls()) # Now includes instrument type
        column2_layout.addWidget(melody_group)

        # --- NEW: Bass Settings Group (Column 2) ---
        bass_group = QGroupBox("Bass Settings")
        bass_group.setFont(self.group_box_font)
        bass_group.setLayout(self.create_bass_settings_controls())
        column2_layout.addWidget(bass_group)

        # Include Parts Group (Column 2)
        include_group = QGroupBox("Include Parts")
        include_group.setFont(self.group_box_font)
        include_layout = QVBoxLayout(include_group)
        include_layout.setSpacing(8)
        include_layout.addLayout(self.create_checkboxes())
        column2_layout.addWidget(include_group)


        # Regenerate Group (Column 2)
        regenerate_group = QGroupBox("Regenerate")
        regenerate_group.setFont(self.group_box_font)
        regenerate_layout = QVBoxLayout(regenerate_group)
        regenerate_layout.setSpacing(8)
        regenerate_layout.addLayout(self.create_regenerate_section())
        column2_layout.addWidget(regenerate_group)

        column2_layout.addStretch(1)
        self.columns_layout.addLayout(column2_layout, 1)

        # --- Add the Two Columns to the Main Layout ---
        self.main_layout.addLayout(self.columns_layout)

        # --- Elements Below the Columns (Spanning) ---
        self.create_chord_display_label()
        self.create_status_label()
        self.main_layout.addSpacing(5)
        self.create_piano_roll_widget() # <<< ADDED PIANO ROLL
        self.main_layout.addSpacing(5)
        self.create_drag_drop_area()
        self.main_layout.addSpacing(10) # Reduced spacing
        self.create_generate_button()

        # --- Bottom Layout (Spanning) ---
        self.main_layout.addStretch(1)
        self.create_bottom_layout()

        self._update_ui_for_style(self.style_combo.currentText())
        self._update_all_tooltips(self.show_tooltips) # Set initial tooltip state for all widgets


    # --- GUI Section Creation Methods (Return Layouts/Widgets) ---
    # --- Helper to set tooltip and store original ---
    def _set_widget_tooltip(self, widget, text):
        widget.setProperty("originalToolTip", text)
        widget.setToolTip(text if self.show_tooltips else "")

    def create_style_key_controls(self):
        h_layout = QHBoxLayout(); h_layout.setSpacing(10)
        style_label = QLabel("Pool Style:");
        self.style_combo = QComboBox();
        self.style_combo.addItems(STYLE_OPTIONS); self.style_combo.setCurrentIndex(0)
        self.style_combo.setMinimumWidth(90)
        self._set_widget_tooltip(self.style_combo, "Select the style defining the available chord pool (Chorgi/Jazzy)") # Tooltip
        self.style_combo.currentTextChanged.connect(self._update_ui_for_style)
        h_layout.addWidget(style_label); h_layout.addWidget(self.style_combo)
        h_layout.addSpacerItem(QSpacerItem(10, 0))

        key_type_label = QLabel("Key Type:");
        self.key_type_group = QButtonGroup(self)
        self.major_radio = QRadioButton("Maj");
        self._set_widget_tooltip(self.major_radio, "Use a major key tonality") # Tooltip
        self.minor_radio = QRadioButton("Min");
        self._set_widget_tooltip(self.minor_radio, "Use a minor key tonality") # Tooltip
        self.major_radio.setChecked(True);
        self.key_type_group.addButton(self.major_radio)
        self.key_type_group.addButton(self.minor_radio)

        key_type_layout = QHBoxLayout(); key_type_layout.setSpacing(5)
        key_type_layout.addWidget(self.major_radio); key_type_layout.addWidget(self.minor_radio)
        key_type_layout.addStretch(0)
        h_layout.addWidget(key_type_label); h_layout.addLayout(key_type_layout)
        h_layout.addSpacerItem(QSpacerItem(10, 0))

        key_root_label = QLabel("Key Root:");
        self.key_root_combo = QComboBox();
        self.key_root_combo.addItems(NOTE_NAMES)
        default_root_index = NOTE_NAMES.index("C") if "C" in NOTE_NAMES else 0
        self.key_root_combo.setCurrentIndex(default_root_index)
        self.key_root_combo.setMinimumWidth(60)
        self._set_widget_tooltip(self.key_root_combo, "Select the root note of the key") # Tooltip
        h_layout.addWidget(key_root_label); h_layout.addWidget(self.key_root_combo)
        h_layout.addStretch(1)
        return h_layout

    def create_structure_controls(self):
        layout = QHBoxLayout(); layout.setSpacing(10)
        num_bars_label = QLabel("Bars:");
        self.num_bars_combo = QComboBox();
        self.num_bars_combo.addItems(NUM_BARS_OPTIONS)
        try: default_bars_index = NUM_BARS_OPTIONS.index("12 Bars")
        except ValueError: default_bars_index = 2
        self.num_bars_combo.setCurrentIndex(default_bars_index); self.num_bars_combo.setMinimumWidth(90)
        self._set_widget_tooltip(self.num_bars_combo, "Select the total length of the progression") # Tooltip
        self.num_bars_combo.currentTextChanged.connect(self._update_ui_for_style)
        layout.addWidget(num_bars_label); layout.addWidget(self.num_bars_combo)
        layout.addSpacerItem(QSpacerItem(10, 0))

        self.complexity_label = QLabel("Complexity:");
        self.complexity_combo = QComboBox();
        self.complexity_combo.addItems(CHORD_COMPLEXITY_OPTIONS); self.complexity_combo.setCurrentIndex(0)
        self.complexity_combo.setMinimumWidth(210)
        self._set_widget_tooltip(self.complexity_combo, "Select chord complexity (affects available pool)") # Tooltip
        layout.addWidget(self.complexity_label); layout.addWidget(self.complexity_combo)

        layout.addSpacerItem(QSpacerItem(10, 0))

        tempo_layout = QHBoxLayout(); tempo_layout.setSpacing(5)
        tempo_label = QLabel("BPM:"); tempo_label.setFont(self.tempo_label_font)
        self.bpm_spinbox = QSpinBox();
        self.bpm_spinbox.setRange(40, 300); self.bpm_spinbox.setValue(90)
        self.bpm_spinbox.setFixedWidth(65);
        self._set_widget_tooltip(self.bpm_spinbox, "Set the Beats Per Minute") # Tooltip
        self.embed_tempo_check = QCheckBox("Embed");
        self.embed_tempo_check.setObjectName("EmbedTempoCheck"); self.embed_tempo_check.setChecked(True)
        self._set_widget_tooltip(self.embed_tempo_check, "Include the BPM information in the MIDI file.") # Tooltip
        tempo_layout.addWidget(tempo_label); tempo_layout.addWidget(self.bpm_spinbox)
        tempo_layout.addWidget(self.embed_tempo_check)
        tempo_layout.addStretch(0)

        layout.addLayout(tempo_layout)
        layout.addStretch(1)
        return layout

    def create_progression_controls(self):
        v_layout = QVBoxLayout()
        v_layout.setSpacing(8)

        row1_layout = QHBoxLayout(); row1_layout.setSpacing(10)
        prog_style_label = QLabel("Prog Style:");
        self.prog_style_combo = QComboBox();
        self.prog_style_combo.addItems(PROG_STYLE_OPTIONS); self.prog_style_combo.setCurrentIndex(0)
        self.prog_style_combo.setMinimumWidth(160)
        self._set_widget_tooltip(self.prog_style_combo, "Select the harmonic structure/template for the progression") # Tooltip
        self.prog_style_combo.currentTextChanged.connect(self._update_ui_for_style)
        row1_layout.addWidget(prog_style_label); row1_layout.addWidget(self.prog_style_combo)
        row1_layout.addSpacerItem(QSpacerItem(15, 0))

        self.chord_rate_label = QLabel("Chord Rate:");
        self.chord_rate_combo = QComboBox();
        self.chord_rate_combo.addItems(CHORD_RATE_OPTIONS); self.chord_rate_combo.setCurrentIndex(0)
        self.chord_rate_combo.setMinimumWidth(90)
        self._set_widget_tooltip(self.chord_rate_combo, "Select how many chords typically occur per bar") # Tooltip
        row1_layout.addWidget(self.chord_rate_label); row1_layout.addWidget(self.chord_rate_combo)
        row1_layout.addStretch(1)
        v_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout(); row2_layout.setSpacing(10)
        self.voicing_label = QLabel("Voicing:");
        self.voicing_style_combo = QComboBox();
        self.voicing_style_combo.addItems(VOICING_STYLE_OPTIONS); self.voicing_style_combo.setCurrentIndex(1)
        self.voicing_style_combo.setMinimumWidth(160)
        self._set_widget_tooltip(self.voicing_style_combo, "Select how chords are voiced (root, inversions, specific types)") # Tooltip
        row2_layout.addWidget(self.voicing_label); row2_layout.addWidget(self.voicing_style_combo)
        row2_layout.addSpacerItem(QSpacerItem(15, 0))

        self.cadence_label = QLabel("Cadence:");
        self.cadence_combo = QComboBox();
        self.cadence_combo.addItems(CADENCE_OPTIONS); self.cadence_combo.setCurrentIndex(0)
        self.cadence_combo.setMinimumWidth(130)
        self._set_widget_tooltip(self.cadence_combo, "Select the desired harmonic ending for the progression") # Tooltip
        row2_layout.addWidget(self.cadence_label); row2_layout.addWidget(self.cadence_combo)
        row2_layout.addStretch(1)
        v_layout.addLayout(row2_layout)

        return v_layout

    def create_chord_bias_control(self):
        layout = QHBoxLayout(); layout.setSpacing(10)
        self.chord_bias_label = QLabel("Chord Bias:");
        self.chord_bias_combo = QComboBox();
        self.chord_bias_combo.addItems(CHORD_BIAS_OPTIONS); self.chord_bias_combo.setCurrentIndex(0)
        self.chord_bias_combo.setMinimumWidth(100)
        self._set_widget_tooltip(self.chord_bias_combo, "Favor darker (minor/dim) or lighter (major) chords (subtle effect)") # Tooltip
        layout.addWidget(self.chord_bias_label); layout.addWidget(self.chord_bias_combo)
        layout.addStretch(1)
        return layout

    def create_arp_controls(self):
         layout = QHBoxLayout(); layout.setSpacing(10)
         arp_style_label = QLabel("Arp Style:");
         self.arp_style_combo = QComboBox();
         self.arp_style_combo.addItems(ARP_STYLE_OPTIONS); self.arp_style_combo.setCurrentIndex(0)
         self.arp_style_combo.setMinimumWidth(170)
         self._set_widget_tooltip(self.arp_style_combo, "Select the note order pattern for the arpeggiator") # Tooltip
         layout.addWidget(arp_style_label); layout.addWidget(self.arp_style_combo)
         layout.addSpacerItem(QSpacerItem(15, 0))
         arp_octave_label = QLabel("Arp Octave:");
         self.arp_octave_combo = QComboBox();
         self.arp_octave_combo.addItems(ARP_OCTAVE_OPTIONS); self.arp_octave_combo.setCurrentIndex(0)
         self.arp_octave_combo.setMinimumWidth(100)
         self._set_widget_tooltip(self.arp_octave_combo, "Select the octave range for the arpeggiator notes relative to the chord") # Tooltip
         layout.addWidget(arp_octave_label); layout.addWidget(self.arp_octave_combo)
         layout.addStretch(1)
         return layout

    def create_melody_controls(self):
        container_layout = QVBoxLayout()
        container_layout.setSpacing(8)

        # Row 1: Generation Style & Instrument
        row1_layout = QHBoxLayout(); row1_layout.setSpacing(10)
        melody_gen_style_label = QLabel("Melody Gen:");
        self.melody_gen_style_combo = QComboBox();
        self.melody_gen_style_combo.addItems(MELODY_GEN_STYLE_OPTIONS); self.melody_gen_style_combo.setCurrentIndex(0)
        self.melody_gen_style_combo.setMinimumWidth(150)
        self._set_widget_tooltip(self.melody_gen_style_combo, "Choose the algorithm used for generating melody notes") # Tooltip
        row1_layout.addWidget(melody_gen_style_label); row1_layout.addWidget(self.melody_gen_style_combo)
        row1_layout.addSpacerItem(QSpacerItem(15, 0))

        melody_instr_label = QLabel("Instrument:"); # NEW
        self.melody_instrument_combo = QComboBox(); # NEW
        self.melody_instrument_combo.addItems(MELODY_INSTRUMENT_OPTIONS); self.melody_instrument_combo.setCurrentIndex(0) # Default None
        self.melody_instrument_combo.setMinimumWidth(100)
        self._set_widget_tooltip(self.melody_instrument_combo, "Select target instrument type (subtly influences generation)") # Tooltip
        row1_layout.addWidget(melody_instr_label); row1_layout.addWidget(self.melody_instrument_combo)
        row1_layout.addStretch(1)
        container_layout.addLayout(row1_layout)

        # Row 2: Octave, Articulation & Speed
        row2_layout = QHBoxLayout(); row2_layout.setSpacing(10)
        melody_octave_label = QLabel("Mel Octave:");
        self.melody_octave_combo = QComboBox();
        self.melody_octave_combo.addItems(MELODY_OCTAVE_OPTIONS); self.melody_octave_combo.setCurrentIndex(0)
        self.melody_octave_combo.setMinimumWidth(70)
        self._set_widget_tooltip(self.melody_octave_combo, "Select the target octave range for the melody") # Tooltip
        row2_layout.addWidget(melody_octave_label); row2_layout.addWidget(self.melody_octave_combo)
        row2_layout.addSpacerItem(QSpacerItem(10, 0)) # Smaller spacer

        melody_style_label = QLabel("Articulation:");
        self.melody_style_combo = QComboBox();
        self.melody_style_combo.addItems(MELODY_STYLE_OPTIONS); self.melody_style_combo.setCurrentIndex(0)
        self.melody_style_combo.setMinimumWidth(100)
        self._set_widget_tooltip(self.melody_style_combo, "Select melody note articulation (Legato: connected, Staccato: short/detached)") # Tooltip
        row2_layout.addWidget(melody_style_label); row2_layout.addWidget(self.melody_style_combo)
        row2_layout.addSpacerItem(QSpacerItem(10, 0)) # Smaller spacer

        melody_speed_label = QLabel("Mel Speed:");
        self.melody_speed_combo = QComboBox();
        self.melody_speed_combo.addItems(MELODY_SPEED_OPTIONS); self.melody_speed_combo.setCurrentIndex(1)
        self.melody_speed_combo.setMinimumWidth(90)
        self._set_widget_tooltip(self.melody_speed_combo, "Control the rhythmic density and speed of the melody") # Tooltip
        row2_layout.addWidget(melody_speed_label); row2_layout.addWidget(self.melody_speed_combo)
        row2_layout.addStretch(1)
        container_layout.addLayout(row2_layout)

        return container_layout

    # --- NEW: Bass Settings Controls ---
    def create_bass_settings_controls(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)
        bass_style_label = QLabel("Bass Style:")
        self.bass_style_combo = QComboBox()
        self.bass_style_combo.addItems(BASS_STYLE_OPTIONS)
        self.bass_style_combo.setCurrentIndex(0) # Default Standard
        self.bass_style_combo.setMinimumWidth(150)
        self._set_widget_tooltip(self.bass_style_combo, "Select the style for the bassline generation")
        layout.addWidget(bass_style_label)
        layout.addWidget(self.bass_style_combo)
        layout.addStretch(1)
        return layout


    def create_checkboxes(self):
        layout = QHBoxLayout(); layout.setSpacing(20);
        layout.addStretch(1)
        self.include_arp_check = QCheckBox("Arpeggio");
        self.include_arp_check.setChecked(self.include_arp)
        self._set_widget_tooltip(self.include_arp_check, "Include the generated arpeggio track in the MIDI output") # Tooltip
        layout.addWidget(self.include_arp_check)
        self.include_melody_check = QCheckBox("Melody");
        self.include_melody_check.setChecked(self.include_melody)
        self._set_widget_tooltip(self.include_melody_check, "Include the generated melody track in the MIDI output") # Tooltip
        layout.addWidget(self.include_melody_check)
        self.include_bass_check = QCheckBox("Bassline");
        self.include_bass_check.setChecked(self.include_bass)
        self._set_widget_tooltip(self.include_bass_check, "Include the generated bassline track in the MIDI output") # Tooltip
        layout.addWidget(self.include_bass_check)
        layout.addStretch(1)
        return layout

    def create_chord_display_label(self):
        self.chord_display_label = QLabel("(Progression will appear here)")
        self.chord_display_label.setObjectName("ChordDisplayLabel") # Stylesheet handles font/bold
        self.chord_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chord_display_label.setWordWrap(True)
        self._set_widget_tooltip(self.chord_display_label, "Shows the generated chord names (without inversions/voicings)") # Tooltip
        self.main_layout.addWidget(self.chord_display_label)

    def create_status_label(self):
        self.status_label = QLabel("Select options and click Generate MIDI")
        self.status_label.setFont(self.status_font) # Use status font
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True);
        self._set_widget_tooltip(self.status_label, "Displays the current status or result of the generation") # Tooltip
        self.main_layout.addWidget(self.status_label)

    # --- NEW: Piano Roll Widget Creation ---
    def create_piano_roll_widget(self):
        self.piano_roll_widget = PianoRollWidget(self) # Pass self as parent
        # Tooltip is set within PianoRollWidget __init__, using parent state
        self.main_layout.addWidget(self.piano_roll_widget)

    def create_drag_drop_area(self):
        self.drag_midi_label = DragMidiLabel(self)
        # Tooltip is set/updated within DragMidiLabel class methods using setProperty
        self.main_layout.addWidget(self.drag_midi_label)

    def create_generate_button(self):
        layout = QHBoxLayout(); layout.addStretch(1)
        self.generate_button = QPushButton("Generate MIDI")
        self.generate_button.setObjectName("GenerateButton"); self.generate_button.setFont(self.button_font)
        self.generate_button.setMinimumWidth(150)
        self._set_widget_tooltip(self.generate_button, "Generate a new MIDI file with the current settings") # Tooltip
        self.generate_button.clicked.connect(self.run_generate_midi_sequence)
        layout.addWidget(self.generate_button); layout.addStretch(1)
        self.main_layout.addLayout(layout)

    def create_regenerate_section(self):
        layout = QHBoxLayout(); layout.setSpacing(10);
        regen_label = QLabel("Regen Part:");
        self.regenerate_part_combo = QComboBox();
        self.regenerate_part_combo.addItems(REGENERATE_PART_OPTIONS); self.regenerate_part_combo.setMinimumWidth(90)
        self._set_widget_tooltip(self.regenerate_part_combo, "Select which part to regenerate using the current settings") # Tooltip
        self.regenerate_button = QPushButton("Regenerate Part")
        self.regenerate_button.setObjectName("RegenerateButton"); self.regenerate_button.setFont(self.button_font)
        self.regenerate_button.setEnabled(False)
        self._set_widget_tooltip(self.regenerate_button, "Regenerate only the selected part (Arp, Melody, or Bass)") # Tooltip
        self.regenerate_button.clicked.connect(self.run_regenerate_selected_parts)
        layout.addWidget(regen_label); layout.addWidget(self.regenerate_part_combo)
        layout.addSpacerItem(QSpacerItem(5, 0)); layout.addWidget(self.regenerate_button)
        layout.addStretch(1)
        return layout

    def create_bottom_layout(self):
        bottom_h_layout = QHBoxLayout(); bottom_h_layout.setContentsMargins(0, 5, 0, 0)
        # Left side: Support/Branding
        left_v_layout = QVBoxLayout(); left_v_layout.setSpacing(2)
        self.support_button = QPushButton("Support"); self.support_button.setObjectName("SupportButton")
        app_version = QCoreApplication.applicationVersion()
        self._set_widget_tooltip(self.support_button, f"Get support information (Version {app_version})") # Tooltip
        self.support_button.clicked.connect(self._show_support_info)
        left_v_layout.addWidget(self.support_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.branding_label = QLabel("Chorgi by Blackfin Audio"); self.branding_label.setFont(self.footer_font) # Explicit normal
        self.branding_label.setObjectName("BrandingLabel"); # Stylesheet handles rest
        left_v_layout.addWidget(self.branding_label)
        left_v_layout.addStretch(1)
        bottom_h_layout.addLayout(left_v_layout)
        bottom_h_layout.addStretch(1)
        # Right side: Theme & Randomize
        right_h_layout = QHBoxLayout(); right_h_layout.setSpacing(10)
        theme_label = QLabel("Theme:");
        self.theme_combo = QComboBox();
        self.theme_combo.addItems(THEME_OPTIONS); self.theme_combo.setCurrentIndex(0) # Default Dark
        self.theme_combo.setMinimumWidth(110)
        self._set_widget_tooltip(self.theme_combo, "Switch between Dark and Light UI themes") # Tooltip
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        right_h_layout.addWidget(theme_label); right_h_layout.addWidget(self.theme_combo)
        right_h_layout.addSpacerItem(QSpacerItem(15, 0))
        self.randomize_button = QPushButton("🎲"); self.randomize_button.setObjectName("RandomizeButton")
        self.randomize_button.setFixedSize(50, 35);
        self._set_widget_tooltip(self.randomize_button, "Randomize all options") # Tooltip
        self.randomize_button.clicked.connect(self.run_randomize_all_options)
        right_h_layout.addWidget(self.randomize_button)
        bottom_h_layout.addLayout(right_h_layout)
        self.main_layout.addLayout(bottom_h_layout)


    # --- Signal Handlers for UI Interaction ---

    def _toggle_tooltips_slot(self, state):
        """Slot to handle the state change of the tooltip checkbox."""
        self.show_tooltips = (state == Qt.CheckState.Checked.value)
        self._update_all_tooltips(self.show_tooltips)

    def _update_all_tooltips(self, enabled):
        """Iterates through widgets and enables/disables tooltips based on stored text."""
        for widget in self.findChildren(QWidget):
            original_tooltip = widget.property("originalToolTip")
            if original_tooltip is not None: # Check if the property was set
                widget.setToolTip(original_tooltip if enabled else "")

    def _apply_theme(self, theme_name):
        """Applies the selected theme (palette and stylesheet)."""
        if "Light" in theme_name:
            selected_palette = self.light_palette
            selected_stylesheet = self.light_stylesheet
        else:
            selected_palette = self.dark_palette
            selected_stylesheet = self.dark_stylesheet

        # Update tooltip display on theme change before applying stylesheet
        self._update_all_tooltips(self.show_tooltips)

        current_drag_text = self.drag_midi_label.text()
        if "Generate MIDI first" in current_drag_text:
             self.drag_midi_label.setText("(Generate MIDI first)")
             # Reset tooltip for drag label specifically
             self._set_widget_tooltip(self.drag_midi_label, "Click and drag the saved MIDI file from here")


        self.setPalette(selected_palette)
        if QApplication.instance(): # Ensure app exists
            QApplication.instance().setPalette(selected_palette) # Apply palette to whole app for consistency
        self.setStyleSheet(selected_stylesheet) # Apply the stylesheet
        # Force update/repaint of widgets that might rely on stylesheet changes
        self.update()
        for widget in self.findChildren(QWidget):
            widget.update()
        # Re-apply tooltip state after stylesheet potentially overrides something
        self._update_all_tooltips(self.show_tooltips)


    def _set_control_enabled(self, control, label_widget, enabled, tooltip_enabled="", reason_disabled=""):
        """Sets enabled state and updates tooltip for a control and its label."""
        control.setEnabled(enabled)
        if label_widget:
            label_widget.setEnabled(enabled) # Ensure label visibility matches control

        # Determine the correct tooltip text based on enabled state
        tooltip_text = tooltip_enabled if enabled else reason_disabled

        # Store the appropriate original tooltip text
        control.setProperty("originalToolTip", tooltip_text)
        if label_widget:
            label_widget.setProperty("originalToolTip", tooltip_text)

        # Set the current tooltip based on the global toggle
        control.setToolTip(tooltip_text if self.show_tooltips else "")
        if label_widget:
            label_widget.setToolTip(tooltip_text if self.show_tooltips else "")


    def _update_ui_for_style(self, changed_text):
        """Enables/disables options based on the selected styles. Triggered by Pool Style or Prog Style."""
        # Determine current selections reliably
        prog_style = self.prog_style_combo.currentText() if hasattr(self, 'prog_style_combo') else PROG_STYLE_OPTIONS[0]
        # pool_style = self.style_combo.currentText() if hasattr(self, 'style_combo') else STYLE_OPTIONS[0] # Not needed for enabling/disabling

        is_blues_prog = (prog_style == "Blues (12 Bar)")

        # --- Control Tooltips (Define once) ---
        tooltip_complexity = "Select chord complexity (affects available pool)"
        reason_complexity_disabled_blues = "Complexity fixed for Blues style (uses 7th chords)"
        tooltip_bias = "Favor darker (minor/dim) or lighter (major) chords (subtle effect)"
        tooltip_num_bars = "Select the total length of the progression"
        reason_num_bars_disabled_blues = "Blues progression is fixed at 12 bars"
        tooltip_cadence = "Select the desired harmonic ending for the progression"
        reason_cadence_disabled_blues = "Blues cadence is part of the fixed progression"
        tooltip_chord_rate = "Select how many chords typically occur per bar"
        reason_chord_rate_disabled_blues = "Blues chord rate is fixed (1/bar)"
        tooltip_voicing = "Select how chords are voiced (root, inversions, specific types)"

        # --- Enable/Disable Controls ---
        # Complexity (Disabled for Blues)
        if hasattr(self, 'complexity_combo') and hasattr(self, 'complexity_label'):
            self._set_control_enabled(
                self.complexity_combo, self.complexity_label,
                enabled=not is_blues_prog,
                tooltip_enabled=tooltip_complexity,
                reason_disabled=reason_complexity_disabled_blues
            )
            if is_blues_prog and self.complexity_combo.count() > 0:
                self.complexity_combo.setCurrentIndex(0) # Reset to standard

        # Chord Bias (Always Enabled - Update tooltip only)
        if hasattr(self, 'chord_bias_combo') and hasattr(self, 'chord_bias_label'):
            self._set_control_enabled(
                self.chord_bias_combo, self.chord_bias_label,
                enabled=True, tooltip_enabled=tooltip_bias
            )

        # Number of Bars (Disabled for Blues)
        num_bars_label_widget = None
        if hasattr(self, 'num_bars_combo'):
             # Find the label associated with num_bars_combo
             # Assume structure: Label, ComboBox, Spacer
             parent_widget = self.num_bars_combo.parentWidget()
             if parent_widget and parent_widget.layout():
                 layout = parent_widget.layout()
                 # Find index of combo box
                 combo_index = -1
                 for i in range(layout.count()):
                     item = layout.itemAt(i)
                     if item and item.widget() == self.num_bars_combo:
                         combo_index = i
                         break
                 # Get the widget at the previous index if it's a QLabel
                 if combo_index > 0:
                     prev_item = layout.itemAt(combo_index - 1)
                     if prev_item and isinstance(prev_item.widget(), QLabel):
                         num_bars_label_widget = prev_item.widget()

             self._set_control_enabled(
                 self.num_bars_combo, num_bars_label_widget,
                 enabled=not is_blues_prog,
                 tooltip_enabled=tooltip_num_bars,
                 reason_disabled=reason_num_bars_disabled_blues
             )
             if is_blues_prog:
                  try:
                      index_12 = NUM_BARS_OPTIONS.index("12 Bars")
                      self.num_bars_combo.setCurrentIndex(index_12)
                  except ValueError:
                      if self.num_bars_combo.count() > 2: self.num_bars_combo.setCurrentIndex(2) # Fallback

        # Cadence (Disabled for Blues)
        if hasattr(self, 'cadence_combo') and hasattr(self, 'cadence_label'):
             self._set_control_enabled(
                self.cadence_combo, self.cadence_label,
                enabled=not is_blues_prog,
                tooltip_enabled=tooltip_cadence,
                reason_disabled=reason_cadence_disabled_blues
            )
             if is_blues_prog and self.cadence_combo.count() > 0:
                 self.cadence_combo.setCurrentIndex(0) # Reset to Any

        # Chord Rate (Disabled for Blues)
        if hasattr(self, 'chord_rate_combo') and hasattr(self, 'chord_rate_label'):
             self._set_control_enabled(
                self.chord_rate_combo, self.chord_rate_label,
                enabled=not is_blues_prog,
                tooltip_enabled=tooltip_chord_rate,
                reason_disabled=reason_chord_rate_disabled_blues
            )
             if is_blues_prog and self.chord_rate_combo.count() > 0:
                 self.chord_rate_combo.setCurrentIndex(0) # Reset to 1/Bar

        # Voicing (Enabled unless you specifically want to disable for Blues)
        if hasattr(self, 'voicing_style_combo') and hasattr(self, 'voicing_label'):
             self._set_control_enabled(
                self.voicing_style_combo, self.voicing_label,
                enabled=True, # Keep enabled even for Blues for now
                tooltip_enabled=tooltip_voicing
            )


    def _show_support_info(self):
        """Displays the support information message box."""
        # (Function remains the same)
        msg_box = QMessageBox(self); msg_box.setWindowTitle("Support Information")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        app_version = QCoreApplication.applicationVersion() # Get version
        msg_box.setText(
            f"Thank you for using Chorgi (v{app_version})!<br><br>" # Added version here too
            "If you have any questions or concerns please reach out to our support email which is currently:<br>"
            "<a href='mailto:kory.drake207@gmail.com'>kory.drake207@gmail.com</a>"
            "<br><br>"
            "<center>Developed by Kory Drake.</center>"
        )
        msg_box.exec()


    # --- GUI Interaction Helper Methods ---
    def show_error_message(self, title, message):
         """Displays an error message box."""
         # (Function remains the same)
         try:
             msgBox = QMessageBox(self); msgBox.setIcon(QMessageBox.Icon.Critical)
             msgBox.setWindowTitle(title); msgBox.setText(message)
             msgBox.exec()
         except Exception as e:
             print(f"Error displaying error message box: {e}\nOriginal Error: {title} - {message}")

    def show_warning_message(self, title, message):
         """Displays a warning message box."""
         # (Function remains the same)
         try:
             msgBox = QMessageBox(self); msgBox.setIcon(QMessageBox.Icon.Warning)
             msgBox.setWindowTitle(title); msgBox.setText(message)
             msgBox.exec()
         except Exception as e:
             print(f"Error displaying warning message box: {e}\nOriginal Warning: {title} - {message}")

    def update_status(self, message):
        """Updates the status label text."""
        # (Function remains the same)
        if hasattr(self, 'status_label'):
             self.status_label.setText(message)
             QCoreApplication.processEvents()

    def set_button_state(self, button, enabled, text=None):
         """Enables/disables a button and optionally changes its text."""
         # (Function remains the same)
         if button:
             button.setEnabled(enabled)
             if text is not None: button.setText(text)

    def update_drag_label(self, file_path):
        """Updates the drag label with the latest file path."""
        # (Function remains the same)
        self.last_saved_midi_path = file_path
        if hasattr(self, 'drag_midi_label'):
            self.drag_midi_label.set_midi_path(file_path) # This already handles tooltips via setProperty


    # --- Core Logic Wrapper Methods ---
    def run_generate_midi_sequence(self):
        """Gets options from GUI, runs generation logic, handles AUTOMATIC saving."""
        if not self.save_directory and not self._get_save_directory():
             self.show_error_message("Save Error", "Cannot generate MIDI without a valid save directory.")
             return
        if hasattr(self, 'chord_display_label'): self.chord_display_label.setText("")
        # Clear piano roll before generation
        if hasattr(self, 'piano_roll_widget'):
            self.piano_roll_widget.set_data([], [], [], [], 16.0)


        # Get Key Info
        key_root_name = self.key_root_combo.currentText()
        is_minor_key = self.minor_radio.isChecked()
        key_type = "minor" if is_minor_key else "major"
        chosen_key_name = key_root_name + ("m" if is_minor_key else "")
        if not key_root_name: self.show_error_message("Input Error", "Please select a Key Root."); return

        try:
            self.set_button_state(self.generate_button, False, "Generating..."); self.set_button_state(self.regenerate_button, False)
            self.update_status("Generating..."); self.update_drag_label(None)

            # --- Get ALL GUI options ---
            pool_style_selection = self.style_combo.currentText() # Chorgi/Jazzy
            complexity_selection = self.complexity_combo.currentText() if self.complexity_combo.isEnabled() else "Standard (Triads/7ths)"
            num_bars_selection = self.num_bars_combo.currentText() if self.num_bars_combo.isEnabled() else "12 Bars"

            # Progression Settings
            prog_style_selection = self.prog_style_combo.currentText()
            chord_rate_selection = self.chord_rate_combo.currentText() if self.chord_rate_combo.isEnabled() else "1 / Bar"
            voicing_style_selection = self.voicing_style_combo.currentText()
            cadence_selection = self.cadence_combo.currentText() if self.cadence_combo.isEnabled() else "Any"

            # Chord Settings
            chord_bias_selection = self.chord_bias_combo.currentText()

            # Bass Settings --- NEW ---
            bass_style_selection = self.bass_style_combo.currentText() if hasattr(self, 'bass_style_combo') else BASS_STYLE_OPTIONS[0]

            # Arp Settings
            arp_style_selection = self.arp_style_combo.currentText()
            arp_octave_selection = self.arp_octave_combo.currentText()

            # Melody Settings
            melody_style_selection = self.melody_style_combo.currentText()
            melody_speed_selection = self.melody_speed_combo.currentText()
            melody_octave_selection = self.melody_octave_combo.currentText()
            melody_gen_style_selection = self.melody_gen_style_combo.currentText()
            melody_instrument_selection = self.melody_instrument_combo.currentText() if hasattr(self, 'melody_instrument_combo') else MELODY_INSTRUMENT_OPTIONS[0]

            # Include Parts
            self.include_arp = self.include_arp_check.isChecked()
            self.include_melody = self.include_melody_check.isChecked()
            self.include_bass = self.include_bass_check.isChecked()

            # Tempo
            bpm_value = self.bpm_spinbox.value()
            embed_tempo = self.embed_tempo_check.isChecked()

            # --- Execute Generation ---
            self.generation_count += 1
            success = self._execute_generation_logic(
                pool_style=pool_style_selection, chosen_key_name=chosen_key_name, key_type=key_type,
                complexity=complexity_selection, num_bars_str=num_bars_selection,
                prog_style=prog_style_selection, chord_rate=chord_rate_selection,
                voicing_style=voicing_style_selection, cadence=cadence_selection,
                chord_bias=chord_bias_selection,
                bass_style=bass_style_selection, # Pass bass style
                arp_style=arp_style_selection, arp_octave=arp_octave_selection,
                melody_gen_style=melody_gen_style_selection, melody_octave=melody_octave_selection,
                melody_articulation=melody_style_selection, melody_speed=melody_speed_selection,
                melody_instrument=melody_instrument_selection, # Pass melody instrument
                include_arp=self.include_arp, include_melody=self.include_melody, include_bass=self.include_bass
            )

            # --- Handle Result and Saving ---
            if success:
                # --- MODIFIED: Chord Display Logic ---
                if hasattr(self, 'chord_display_label') and self.generated_chords_progression:
                    # Extract base chord names robustly (before first '/')
                    chord_names = [prog[0].split('/')[0] for prog in self.generated_chords_progression if prog[0]] # prog[0] is display_name
                    display_limit = 16 # Show more chords if possible
                    display_text = ""
                    num_chords = len(chord_names)

                    if chord_rate_selection == "1 / Bar" or prog_style_selection == "Blues (12 Bar)":
                        display_text = " | ".join(chord_names[:display_limit])
                        if num_chords > display_limit: display_text += " | ..."
                    else: # 2 / Bar - group them
                        grouped_names = []
                        limit_bars = display_limit // 2
                        for i in range(0, num_chords, 2):
                            if i+1 < num_chords:
                                grouped_names.append(f"{chord_names[i]} {chord_names[i+1]}")
                            else:
                                grouped_names.append(chord_names[i]) # Handle odd number
                            if len(grouped_names) >= limit_bars: break # Limit bars shown
                        display_text = " | ".join(grouped_names)
                        if num_chords > display_limit: display_text += " | ..." # Check original limit

                    self.chord_display_label.setText(f"Progression: {display_text}")
                elif hasattr(self, 'chord_display_label'):
                    self.chord_display_label.setText("(Progression generated, but display failed)")
                # --- END MODIFIED Chord Display ---

                # --- Update Piano Roll ---
                if hasattr(self, 'piano_roll_widget'):
                    total_beats = self.last_generated_num_bars * 4.0
                    # FIX: Always pass generated chords if generation was successful
                    self.piano_roll_widget.set_data(
                        self.generated_chords_progression, # Always pass chords
                        self.generated_arp_midi_data if self.include_arp else [],
                        self.generated_bass_midi_data if self.include_bass else [],
                        self.generated_melody_midi_data if self.include_melody else [],
                        total_beats
                    )

                # Generate Filename
                prog_tag = f"_{prog_style_selection.split(' ')[0]}" # e.g., _Pop, _Blues
                rate_tag = "_2cbr" if chord_rate_selection == "2 / Bar" else ""
                complexity_tag = "_Ext" if complexity_selection == "Extra (Extensions)" else ""
                output_filename_base = f"{self.last_generated_key}{prog_tag}{rate_tag}{complexity_tag}_{self.last_generated_num_bars}B"

                if self.include_bass and self.generated_bass_midi_data: output_filename_base += f"_B({bass_style_selection.split(' ')[0]})" # Add bass style
                if self.include_arp and self.generated_arp_midi_data: output_filename_base += "_A"
                if self.include_melody and self.generated_melody_midi_data:
                    instr_tag = melody_instrument_selection[0] if melody_instrument_selection != "None" else ""
                    output_filename_base += f"_M({melody_gen_style_selection.split()[0][0]}{instr_tag})" # Add melody instr initial

                safe_filename_base = "".join(c for c in output_filename_base if c.isalnum() or c in ('_', '-')).rstrip()
                output_filename = f"{safe_filename_base}_{self.generation_count}.mid"
                output_path = os.path.join(self.save_directory, output_filename)

                # Write MIDI
                self._execute_write_midi_file(
                    output_path, self.include_arp, self.include_melody, self.include_bass,
                    melody_style_selection, melody_speed_selection, bpm_value, embed_tempo
                )

                # Update Status/UI
                try: # Display relative path
                    home_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation) or os.path.expanduser("~")
                    display_folder = os.path.relpath(self.save_directory, home_path)
                    if not display_folder.startswith(".."): display_folder = f"~{os.sep}{display_folder}"
                    else: display_folder = f"...{os.sep}{os.path.basename(self.save_directory)}"
                except Exception: display_folder = self.save_directory # Fallback to full path
                self.update_status(f"Success! Saved:\n{output_filename}\nto {display_folder}"); self.update_drag_label(output_path)
                self.set_button_state(self.regenerate_button, True); self.last_generated_filename_base = safe_filename_base

        # --- Error Handling ---
        except ValueError as ve:
            print(f"Value ERROR: {ve}"); traceback.print_exc(); self.show_error_message("Input Error", f"Check settings:\n{ve}"); self.update_status("Error: Invalid input."); self.update_drag_label(None) # Clear drag label
            if hasattr(self, 'chord_display_label'): self.chord_display_label.setText("(Generation Failed)")
            if hasattr(self, 'piano_roll_widget'): self.piano_roll_widget.set_data([],[],[],[], 16.0) # Clear piano roll
        except RuntimeError as re:
            print(f"Runtime ERROR: {re}"); traceback.print_exc(); self.show_error_message("Generation Error", f"{re}"); self.update_status(f"Error: {re}"); self.update_drag_label(None)
            if hasattr(self, 'chord_display_label'): self.chord_display_label.setText("(Generation Failed)")
            if hasattr(self, 'piano_roll_widget'): self.piano_roll_widget.set_data([],[],[],[], 16.0) # Clear piano roll
        except Exception as e:
            print(f"ERROR: {e}"); traceback.print_exc(); self.show_error_message("Error", f"Unexpected error:\n{e}"); self.update_status("Error. See console."); self.update_drag_label(None)
            if hasattr(self, 'chord_display_label'): self.chord_display_label.setText("(Generation Failed)")
            if hasattr(self, 'piano_roll_widget'): self.piano_roll_widget.set_data([],[],[],[], 16.0) # Clear piano roll
        finally:
            self.set_button_state(self.generate_button, True, "Generate MIDI")
            # Enable regenerate only if a progression was successfully stored
            self.set_button_state(self.regenerate_button, bool(self.generated_chords_progression), "Regenerate Part")


    # --- REFACTORED Generation Logic ---
    def _execute_generation_logic(self, pool_style, chosen_key_name, key_type, complexity, num_bars_str,
                                 prog_style, chord_rate, voicing_style, cadence, chord_bias,
                                 bass_style, # Added bass style
                                 arp_style, arp_octave,
                                 melody_gen_style, melody_octave, melody_articulation, melody_speed, melody_instrument, # Added melody instrument
                                 include_arp, include_melody, include_bass):
        """Internal method containing the core generation steps, using new parameters."""
        self.generated_chords_progression = []; self.generated_arp_midi_data = []; self.generated_bass_midi_data = []; self.generated_melody_midi_data = []
        try:
            num_bars = int(num_bars_str.split()[0])
        except: num_bars = 12; print("Warning: Defaulting to 12 bars.")

        is_minor_key = (key_type == "minor")
        chosen_key_root_name = chosen_key_name[:-1] if is_minor_key and chosen_key_name.endswith('m') else chosen_key_name
        if chosen_key_root_name not in ROOT_NOTES_MIDI: raise ValueError(f"Invalid key root: {chosen_key_root_name}")
        chosen_key_root_midi = ROOT_NOTES_MIDI[chosen_key_root_name]
        self.update_status(f"Generating {num_bars} bars: {chosen_key_name} ({prog_style} / {pool_style} Pool)...")

        chord_pool = {}
        pool_chord_names = []

        # --- 1. Generate Chord Pool OR Handle Blues ---
        if prog_style == "Blues (12 Bar)":
            if num_bars != 12: print("Warning: Blues style selected, forcing 12 bars.")
            num_bars = 12 # Ensure blues is 12 bars
            self.update_status(f"Generating 12 bars: {chosen_key_name} (Blues)...") # Update status for blues
            # Use the dedicated blues pool generator
            chord_pool = generate_blues_chord_pool(chosen_key_root_name, chosen_key_root_midi, key_type)
            if not chord_pool: raise RuntimeError("Failed to generate blues chord pool.")
            # Generate the blues progression directly using the blues pool
            self._generate_12_bar_blues_progression(chord_pool, key_type, chosen_key_root_name) # This fills self.generated_chords_progression
            # For Blues, the pool style doesn't strictly matter for chords, but might affect bass/melody later
            # We'll use the 'Chorgi' default if Blues is selected for consistency elsewhere
            pool_style = "Chorgi" # Override pool style for consistency downstream if needed

        else: # Handle non-blues progression styles
            if pool_style == "Jazzy":
                if is_minor_key: chord_pool = generate_jazz_minor_chord_pool(chosen_key_root_name, chosen_key_root_midi, complexity)
                else: chord_pool = generate_jazz_major_chord_pool(chosen_key_root_name, chosen_key_root_midi, complexity)
            else: # Default to Chorgi
                if is_minor_key: chord_pool = generate_chorgi_minor_chord_pool(chosen_key_root_name, chosen_key_root_midi, complexity)
                else: chord_pool = generate_chorgi_major_chord_pool(chosen_key_root_name, chosen_key_root_midi, complexity)

            if not chord_pool: raise RuntimeError(f"Failed to generate chord pool for {pool_style} style.")
            pool_chord_names = list(chord_pool.keys())

            self.generated_chords_progression = self._generate_progression(
                num_bars, prog_style, chord_rate, voicing_style, cadence, chord_bias,
                chord_pool, pool_chord_names, key_type, chosen_key_root_name, is_minor_key
            )

        if not self.generated_chords_progression:
            raise RuntimeError(f"Failed to generate chord progression for {prog_style}.")

        # --- 3. Generate Scale Notes (Needed for other parts) ---
        if is_minor_key: scale_notes = get_natural_minor_scale_notes(chosen_key_root_midi)
        else: scale_notes = get_major_scale_notes(chosen_key_root_midi)
        if not scale_notes: raise RuntimeError(f"Failed to generate diatonic scale notes for {chosen_key_name}.")

        # --- 4. Generate Other Parts ---
        if include_arp:
            self.update_status("Generating Arp...")
            self._generate_arpeggio(arp_style, arp_octave, scale_notes)

        if include_melody:
            self.update_status("Generating Melody...")
            melody_func_map = {
                "Chord Tone Focus": generate_melody_chord_focus,
                "Scale Walker": generate_melody_scale_walker,
                "Experimental": generate_melody_experimental,
                "Leaps & Steps": generate_melody_leaps_steps,
                "Minimalist": generate_melody_minimalist,
                "Sustained Lead": generate_melody_sustained_lead,
                # "Jazz Licks": generate_melody_jazz_licks # Removed
            }
            melody_func = melody_func_map.get(melody_gen_style)
            if melody_gen_style == "Random Style":
                valid_funcs = [f for name, f in melody_func_map.items() if callable(f)]
                if not valid_funcs: raise RuntimeError("No valid melody functions found for Random Style.")
                melody_func = random.choice(valid_funcs)
            elif not melody_func or not callable(melody_func):
                print(f"Warning: Melody function for '{melody_gen_style}' not found or not callable. Using Chord Tone Focus.")
                melody_func = generate_melody_chord_focus

            # --- Pass melody_instrument ---
            self.generated_melody_midi_data = melody_func(self.generated_chords_progression, scale_notes, melody_articulation, melody_speed, melody_octave, melody_instrument)

        if include_bass:
            self.update_status("Generating Bassline...")
            # --- NEW: Select bass function based on style ---
            bass_func_map = {
                "Standard": generate_bass_standard,
                "Walking (Jazz)": generate_bass_walking,
                "Pop": generate_bass_pop,
                "RnB": generate_bass_rnb,
                "Hip Hop": generate_bass_hip_hop,
                "808": generate_bass_808
            }
            bass_func = bass_func_map.get(bass_style, generate_bass_standard) # Default to standard
            # Pass scale notes if needed (only walking uses it currently)
            if bass_style == "Walking (Jazz)":
                 self.generated_bass_midi_data = bass_func(self.generated_chords_progression, scale_notes)
            else:
                 # Pass scale_notes as some basslines might use them optionally
                 self.generated_bass_midi_data = bass_func(self.generated_chords_progression, scale_notes)

        else: self.generated_bass_midi_data = []

        # --- Store Last Used Settings ---
        self.last_generated_key = chosen_key_name; self.last_generated_key_type = key_type
        self.last_generated_num_bars = num_bars; self.last_complexity_selection = complexity
        self.last_style_selection = pool_style # Store the pool style used (or implied for Blues)
        # Store other new settings if needed for regeneration later
        self.include_arp = include_arp; self.include_melody = include_melody; self.include_bass = include_bass
        return True


    # --- Refactored Core Progression Generation (Blues check removed) ---
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< FIXED FUNCTION >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def _generate_progression(self, num_bars, prog_style, chord_rate_str, voicing_style, cadence_str,
                             chord_bias, chord_pool, pool_chord_names, key_type, key_root_name, is_minor):
        """Generates the chord progression based on selected style, rate, voicing, cadence."""
        # NOTE: This function is NO LONGER called if prog_style is "Blues (12 Bar)"

        progression_data = []
        chords_per_bar = 1 if chord_rate_str == "1 / Bar" else 2
        total_chord_slots = num_bars * chords_per_bar
        beats_per_chord = 4.0 / chords_per_bar

        chord_octave_shift = -12 # Standard shift for MIDI playback

        previous_chord_notes_original = None # Store root position notes here
        previous_chord_final_notes = None    # Store voiced/inverted notes here
        previous_chord_name_base = None

        # --- Define Template Sequences (as functions/chord names) ---
        pop_sequence = ['I', 'vi', 'IV', 'V']
        pachelbel_sequence = ['I', 'V', 'vi', 'iii', 'IV', 'I', 'IV', 'V']
        ii_v_i_basic = ['ii', 'V', 'I']

        current_slot = 0
        while current_slot < total_chord_slots:

            chord_name = None
            original_notes = None # Root position notes of the selected chord
            final_voiced_notes = None # Notes after voicing/inversion
            midi_notes = None
            root_note = None
            display_name = None # Includes inversion/voicing info

            # --- Apply Template Logic ---
            if prog_style == "Pop (I-vi-IV-V)":
                func = pop_sequence[current_slot % len(pop_sequence)]
                chord_name = _find_chord_by_function(chord_pool, func, key_type)
            elif prog_style == "Pachelbel-ish":
                 func = pachelbel_sequence[current_slot % len(pachelbel_sequence)]
                 chord_name = _find_chord_by_function(chord_pool, func, key_type)
            elif prog_style == "ii-V-I Focused":
                 sub_cycle = current_slot % 3
                 func = ii_v_i_basic[sub_cycle]
                 chord_name = _find_chord_by_function(chord_pool, func, key_type)
            # Default to "Smooth Random" if no template applies or fails
            if not chord_name or prog_style == "Smooth Random":
                 # --- Corrected call to _find_next_smooth_chord (already expects 6 return values) ---
                 chord_name, original_notes, final_voiced_notes, midi_notes, display_name, root_note = self._find_next_smooth_chord(
                     chord_pool, pool_chord_names, previous_chord_final_notes, previous_chord_name_base, # Pass final notes of prev chord
                     chord_bias, key_root_name, voicing_style, chord_octave_shift # Pass shift
                 )

            # If a chord name was found by template, get its data and apply voicing
            elif chord_name: # If template found a name, but smooth logic didn't run
                if chord_name in chord_pool:
                    chord_data = chord_pool[chord_name] # Get chord data
                    original_notes_template = chord_data.get('notes') # Store root position
                    if original_notes_template:
                        # Apply voicing based on selection
                        # ----- FIX: Unpack all 5 return values -----
                        original_notes, final_voiced_notes, midi_notes, root_note, display_name = self._apply_voicing(
                            original_notes_template, voicing_style, chord_name, chord_octave_shift
                        )
                    else:
                        print(f"Warning: Template chord '{chord_name}' has no notes in pool. Skipping slot {current_slot}.")
                        chord_name = None # Mark as failed
                else:
                    print(f"Warning: Template chord '{chord_name}' not in pool. Skipping slot {current_slot}.")
                    chord_name = None # Mark as failed

            # --- Handle Failed Chord Selection ---
            if not chord_name or not original_notes or not final_voiced_notes:
                 fallback_choice = previous_chord_name_base if previous_chord_name_base and previous_chord_name_base in chord_pool else random.choice(pool_chord_names) if pool_chord_names else None
                 if fallback_choice and fallback_choice in chord_pool:
                     chord_name = fallback_choice
                     original_notes_fallback = chord_pool[chord_name].get('notes')
                     if original_notes_fallback:
                         # ----- FIX: Unpack all 5 return values -----
                         original_notes, final_voiced_notes, midi_notes, root_note, display_name = self._apply_voicing(
                             original_notes_fallback, voicing_style, chord_name, chord_octave_shift
                         )
                         print(f"Warning: Falling back to '{chord_name}' for slot {current_slot}.")
                     else:
                         print(f"ERROR: Fallback chord '{chord_name}' has no notes. Stopping.")
                         break
                 else:
                     print(f"ERROR: Cannot find any chord for slot {current_slot}. Stopping.")
                     break

            # --- Store Chord ---
            # Ensure all components are valid before appending
            if chord_name and original_notes and midi_notes and final_voiced_notes and root_note is not None:
                 if display_name is None: display_name = chord_name
                 # Store the *original_notes* (root position) and the *midi_notes* (voiced & shifted)
                 progression_data.append( (display_name, original_notes, midi_notes, root_note, beats_per_chord) )
                 # --- Update previous state for smoothness calculation ---
                 previous_chord_final_notes = final_voiced_notes # Use the final voiced notes for next comparison
                 previous_chord_name_base = chord_name.split('/')[0] # Use base name without voicing info
            else:
                 print(f"ERROR: Failed to store data for slot {current_slot}. Chord: {chord_name}")
                 progression_data.append(("ERROR", [], [], None, beats_per_chord)) # Add placeholder
                 previous_chord_final_notes = None # Reset previous state on error
                 previous_chord_name_base = None


            current_slot += 1

        # --- Apply Cadence ---
        if cadence_str != "Any" and len(progression_data) >= 2:
            tonic_chord_name = _find_chord_by_function(chord_pool, 'I', key_type, prefer_seventh=False)
            # Adjust tonic name based on key type (basic adjustment)
            if tonic_chord_name:
                if is_minor and not tonic_chord_name.endswith('m') and not tonic_chord_name.endswith('m7') and 'dim' not in tonic_chord_name and 'ø' not in tonic_chord_name: tonic_chord_name += 'm'
                elif not is_minor and (tonic_chord_name.endswith('m') or tonic_chord_name.endswith('m7')): tonic_chord_name = tonic_chord_name.replace('m7','').replace('m','')

            dom_chord_name = _find_chord_by_function(chord_pool, 'V', key_type, prefer_seventh=True)
            subdom_chord_name = _find_chord_by_function(chord_pool, 'IV', key_type)

            tonic_data = chord_pool.get(tonic_chord_name)
            dom_data = chord_pool.get(dom_chord_name)
            subdom_data = chord_pool.get(subdom_chord_name)

            if cadence_str == "Authentic (V-I)" and dom_data and tonic_data and tonic_data.get('notes') and dom_data.get('notes'):
                 last_slot_idx = len(progression_data) - 1
                 # ----- FIX: Unpack all 5 return values -----
                 t_orig, t_final, t_midi, t_root, t_disp = self._apply_voicing(tonic_data['notes'], voicing_style, tonic_chord_name, chord_octave_shift)
                 progression_data[last_slot_idx] = (t_disp, t_orig, t_midi, t_root, beats_per_chord)
                 if last_slot_idx > 0:
                     # ----- FIX: Unpack all 5 return values -----
                     v_orig, v_final, v_midi, v_root, v_disp = self._apply_voicing(dom_data['notes'], voicing_style, dom_chord_name, chord_octave_shift)
                     progression_data[last_slot_idx - 1] = (v_disp, v_orig, v_midi, v_root, beats_per_chord)

            elif cadence_str == "Plagal (IV-I)" and subdom_data and tonic_data and tonic_data.get('notes') and subdom_data.get('notes'):
                 last_slot_idx = len(progression_data) - 1
                 # ----- FIX: Unpack all 5 return values -----
                 t_orig, t_final, t_midi, t_root, t_disp = self._apply_voicing(tonic_data['notes'], voicing_style, tonic_chord_name, chord_octave_shift)
                 progression_data[last_slot_idx] = (t_disp, t_orig, t_midi, t_root, beats_per_chord)
                 if last_slot_idx > 0:
                     # ----- FIX: Unpack all 5 return values -----
                     iv_orig, iv_final, iv_midi, iv_root, iv_disp = self._apply_voicing(subdom_data['notes'], voicing_style, subdom_chord_name, chord_octave_shift)
                     progression_data[last_slot_idx - 1] = (iv_disp, iv_orig, iv_midi, iv_root, beats_per_chord)

        return progression_data
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< END FIXED FUNCTION >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


    # --- HELPER: Apply Voicing (used by templates/cadences) ---
    def _apply_voicing(self, root_pos_notes, voicing_style, base_name, chord_octave_shift):
        """Applies selected voicing style to root position notes."""
        if not root_pos_notes: # Handle empty input
            return [], [], [], None, base_name

        num_n = len(root_pos_notes)
        inv_num = 0
        final_notes = list(root_pos_notes) # Start with root
        display_name = base_name

        if voicing_style == "Allow Inversions":
            max_inv = num_n - 1
            inv_num = random.randint(0, max_inv) if max_inv > 0 and random.random() < 0.6 else 0
            final_notes = calculate_inversion(root_pos_notes, inv_num)
            if inv_num > 0: display_name += f"/Inv{inv_num}"
        elif voicing_style == "Prefer Drop 2" and num_n == 4:
            drop2_notes = calculate_drop2_voicing(root_pos_notes)
            if drop2_notes:
                final_notes = drop2_notes
                display_name += f"/D2"
            # else keep root position
        # "Root Position" is the default if others don't apply

        midi_notes = transpose_notes(final_notes, chord_octave_shift)
        root_note = root_pos_notes[0]
        # Return original root_pos_notes AND the final voiced notes
        return root_pos_notes, final_notes, midi_notes, root_note, display_name


    # --- REFACTORED Smooth Chord Finder ---
    def _find_next_smooth_chord(self, chord_pool, pool_chord_names, prev_notes_voiced, prev_name,
                                chord_bias, key_root_name, voicing_style, chord_octave_shift):
        """Finds the next smoothest chord, applies voicing, and returns all necessary info."""
        num_candidates_smooth = 5
        min_dist_con, best_con_notes_voiced, best_con_name_disp, best_con_root, best_con_orig_notes = float('inf'), None, None, None, None
        min_dist_uncon, best_uncon_notes_voiced, best_uncon_name_disp, best_uncon_root, best_uncon_orig_notes = float('inf'), None, None, None, None
        con_met = False

        if prev_notes_voiced is None: # First chord case
            chosen_start = random.choice(pool_chord_names) if pool_chord_names else None
            if chosen_start and chosen_start in chord_pool:
                 root_pos = chord_pool[chosen_start].get('notes')
                 if root_pos:
                     # Correctly unpacks 5 values here
                     orig_notes, final_voiced, midi_notes, root_note, disp_name = self._apply_voicing(
                         root_pos, voicing_style, chosen_start, chord_octave_shift
                     )
                     # <<< FIX: Need to use the base name for chord_name return >>>
                     base_name = disp_name.split('/')[0]
                     return base_name, orig_notes, final_voiced, midi_notes, disp_name, root_note
            return "ERROR", [], [], [], "ERR", None

        # Smoothness Logic
        prev_avg = get_average_pitch(prev_notes_voiced); prev_high = max(prev_notes_voiced)
        poss_cands = [n for n in pool_chord_names if n != prev_name] or pool_chord_names
        if not poss_cands: return "ERROR", [], [], [], "ERR", None
        num_samp = min(num_candidates_smooth, len(poss_cands)); candidates = random.sample(poss_cands, num_samp)

        for cand_name in candidates:
            if cand_name in chord_pool:
                root_pos = chord_pool[cand_name].get('notes');
                if not root_pos: continue
                num_n = len(root_pos);
                if num_n == 0: continue
                cur_root_bass = root_pos[0]

                # Apply voicing based on selection *before* checking smoothness
                # Correctly unpacks 5 values here
                cand_orig_notes, cand_notes_voiced, _, _, cand_disp = self._apply_voicing(
                    root_pos, voicing_style, cand_name, chord_octave_shift # Shift doesn't matter for smoothness check
                )

                if not cand_notes_voiced: continue

                cand_avg = get_average_pitch(cand_notes_voiced); dist = abs(cand_avg - prev_avg)
                cand_high = max(cand_notes_voiced)

                # Bias
                if chord_bias == "Darker":
                    is_dark = any(k in cand_name.lower() for k in ["m", "dim", "ø", "alt", "b9", "sus"]) and not any(k in cand_name.lower() for k in ["maj", "6"])
                    if is_dark: dist *= 0.7
                elif chord_bias == "Lighter":
                    is_light = ("maj" in cand_name.lower() or cand_name.endswith(key_root_name)) and not any(k in cand_name.lower() for k in ["m", "dim", "ø", "alt", "b9", "sus"])
                    if is_light: dist *= 0.7

                meets_con = cand_high <= prev_high + 3
                if meets_con:
                    con_met = True
                    if dist < min_dist_con:
                        min_dist_con = dist; best_con_notes_voiced = cand_notes_voiced; best_con_name_disp = cand_disp
                        best_con_root = cur_root_bass; best_con_orig_notes = cand_orig_notes
                if dist < min_dist_uncon:
                    min_dist_uncon = dist; best_uncon_notes_voiced = cand_notes_voiced; best_uncon_name_disp = cand_disp
                    best_uncon_root = cur_root_bass; best_uncon_orig_notes = cand_orig_notes

        # Choose best candidate and calculate final MIDI notes
        if con_met and best_con_notes_voiced:
             base_name = best_con_name_disp.split('/')[0]
             final_midi_notes = transpose_notes(best_con_notes_voiced, chord_octave_shift)
             return base_name, best_con_orig_notes, best_con_notes_voiced, final_midi_notes, best_con_name_disp, best_con_root
        elif best_uncon_notes_voiced:
             base_name = best_uncon_name_disp.split('/')[0]
             final_midi_notes = transpose_notes(best_uncon_notes_voiced, chord_octave_shift)
             return base_name, best_uncon_orig_notes, best_uncon_notes_voiced, final_midi_notes, best_uncon_name_disp, best_uncon_root
        else: # Fallback
            fallback_choice = prev_name if prev_name and prev_name in chord_pool else random.choice(pool_chord_names) if pool_chord_names else None
            if fallback_choice and fallback_choice in chord_pool:
                 root_pos = chord_pool[fallback_choice].get('notes')
                 if root_pos:
                     # Correctly unpacks 5 values here
                     orig_notes, final_voiced, midi_notes, root_note, disp_name = self._apply_voicing(
                         root_pos, voicing_style, fallback_choice, chord_octave_shift
                     )
                     # <<< FIX: Need to use the base name for chord_name return >>>
                     base_name = disp_name.split('/')[0]
                     return base_name, orig_notes, final_voiced, midi_notes, disp_name, root_note
            return "ERROR", [], [], [], "ERR", None


    # --- MODIFIED Blues generation to use known names ---
    def _generate_12_bar_blues_progression(self, chord_pool, key_type, key_root_name):
        """Generates data for a 12-bar blues progression using the specific blues pool."""
        progression_data = []
        is_minor_key = (key_type == "minor")
        chord_octave_shift = -12
        beats_per_chord = 4.0

        # Define the EXACT names generated by generate_blues_chord_pool
        if is_minor_key:
            tonic_chord_name = f"{key_root_name}m7"
            subdom_chord_name = f"{NOTE_NAMES[(ROOT_NOTES_MIDI[key_root_name] + 5) % 12]}m7"
            dom_chord_name = f"{NOTE_NAMES[(ROOT_NOTES_MIDI[key_root_name] + 7) % 12]}7"
        else: # Major key
            tonic_chord_name = f"{key_root_name}7"
            subdom_chord_name = f"{NOTE_NAMES[(ROOT_NOTES_MIDI[key_root_name] + 5) % 12]}7"
            dom_chord_name = f"{NOTE_NAMES[(ROOT_NOTES_MIDI[key_root_name] + 7) % 12]}7"

        # Check if they exist in the provided pool (should always, if blues pool was generated)
        required_names = {tonic_chord_name, subdom_chord_name, dom_chord_name}
        if not required_names.issubset(chord_pool.keys()):
            raise RuntimeError(f"Blues chord pool is missing expected chords. Pool: {list(chord_pool.keys())}, Expected: {required_names}")

        # Simple Standard Blues Pattern using the exact names
        pattern_standard = [ tonic_chord_name, tonic_chord_name, tonic_chord_name, tonic_chord_name,
                             subdom_chord_name, subdom_chord_name, tonic_chord_name, tonic_chord_name,
                             dom_chord_name, subdom_chord_name, tonic_chord_name, dom_chord_name ]

        for bar_index in range(12):
            chord_name = pattern_standard[bar_index]
            # No need to check if chord_name is in pool, we did it above
            chord_data = chord_pool[chord_name]
            root_pos_notes = chord_data.get('notes')
            if not root_pos_notes: # Should not happen if pool generation is correct
                 print(f"Warning: Chord '{chord_name}' has no notes. Bar {bar_index + 1}. Using placeholder.")
                 progression_data.append((f"ERR_EMPTY_{chord_name}", [], [], None, beats_per_chord)); continue

            # Apply basic voicing (root position for simplicity in blues)
            final_notes_for_midi = list(root_pos_notes)
            midi_notes = transpose_notes(final_notes_for_midi, chord_octave_shift)
            chord_root_note_for_bass = root_pos_notes[0]
            display_name = chord_name # Use the actual chord name

            progression_data.append((display_name, root_pos_notes, midi_notes, chord_root_note_for_bass, beats_per_chord))

        self.generated_chords_progression = progression_data # Store it


    # --- MODIFIED Arp Generation to use new progression data ---
    def _generate_arpeggio(self, arp_style_selection, arp_octave_selection, scale_notes):
        """Generates the arpeggio using DIATONIC notes, respecting chord durations."""
        if not scale_notes: print("Warning: Cannot generate Arp without diatonic scale notes."); self.generated_arp_midi_data = []; return
        scale_note_pcs = {n % 12 for n in scale_notes}

        oct_shifts = [0];
        if "+1 Octave" in arp_octave_selection: oct_shifts.append(12)
        elif "-1 Octave" in arp_octave_selection: oct_shifts.append(-12)
        # ... (rest of octave logic remains the same)
        elif "+2 Octaves" in arp_octave_selection: oct_shifts.extend([12, 24])
        elif "-2 Octaves" in arp_octave_selection: oct_shifts.extend([-12, -24])
        elif "+3 Octaves" in arp_octave_selection: oct_shifts.extend([12, 24, 36])
        elif "-3 Octaves" in arp_octave_selection: oct_shifts.extend([-12, -24, -36])

        patt_func = None
        if arp_style_selection == "Random (Consistent)": patt_func = random.choice(arp_pattern_functions_list or [get_ascending_pattern])
        elif arp_style_selection == "Random (Per Bar)": patt_func = None # Chosen in loop
        elif arp_style_selection in arp_pattern_functions_map: patt_func = arp_pattern_functions_map[arp_style_selection]
        else: patt_func = random.choice(arp_pattern_functions_list or [get_ascending_pattern])

        self.generated_arp_midi_data = []; current_abs_time = 0.0; volume_arp = 95
        # --- NEW: Arp rhythm options (simple 8ths/16ths for now) ---
        arp_note_durations = [0.5, 0.25] # Eighths, Sixteenths

        for chord_idx, (_, chord_notes_orig, _, _, duration_beats) in enumerate(self.generated_chords_progression):
            chord_start_time = current_abs_time
            if not chord_notes_orig or duration_beats <= 0: # Added duration check
                current_abs_time += duration_beats if duration_beats > 0 else 1.0; continue

            diatonic_notes_in_chord = sorted([n for n in chord_notes_orig if n % 12 in scale_note_pcs])
            if not diatonic_notes_in_chord:
                if chord_notes_orig: # If original notes exist but aren't diatonic
                    root_note = chord_notes_orig[0]
                    if root_note % 12 in scale_note_pcs: diatonic_notes_in_chord = [root_note]
                    else: current_abs_time += duration_beats; continue # Skip chord
                else:
                    current_abs_time += duration_beats; continue # Skip chord if no original notes

            arp_pool = sorted(list(set([n + s for n in diatonic_notes_in_chord for s in oct_shifts if 0 <= n + s <= 127])))
            pool_size = len(arp_pool);
            if pool_size == 0: current_abs_time += duration_beats; continue

            bar_patt_func = patt_func
            if arp_style_selection == "Random (Per Bar)": bar_patt_func = random.choice(arp_pattern_functions_list or [get_ascending_pattern])
            if bar_patt_func is None: bar_patt_func = get_ascending_pattern

            patt_indices = bar_patt_func(pool_size)
            if not patt_indices: current_abs_time += duration_beats; continue

            patt_idx_ctr = 0; time_in_chord = 0.0
            while time_in_chord < duration_beats - 0.01:
                # Choose a note duration (e.g., random 8th or 16th)
                note_dur = random.choice(arp_note_durations)
                act_dur = min(note_dur, duration_beats - time_in_chord) # Ensure it fits
                if act_dur <= 0.01: break # No space left

                note_start_abs = chord_start_time + time_in_chord

                cur_patt_idx = patt_idx_ctr % len(patt_indices); note_idx = patt_indices[cur_patt_idx]
                if 0 <= note_idx < pool_size:
                    pitch = arp_pool[note_idx];
                    vel = max(0, min(127, volume_arp + random.randint(-5, 5)))
                    self.generated_arp_midi_data.append((pitch, note_start_abs, act_dur, vel)) # Store note
                    patt_idx_ctr += 1
                else: # Should not happen if indices are correct
                    patt_idx_ctr += 1

                time_in_chord += note_dur # Advance time by chosen duration

            current_abs_time += duration_beats # Move to the start of the next chord slot


    # --- MODIFIED MIDI Writing to use chord duration ---
    def _execute_write_midi_file(self, output_path, include_arp, include_melody, include_bass, melody_style, melody_speed, bpm_value, embed_tempo):
        """Internal method to write the combined MIDI file, respecting chord durations."""
        num_tracks = 1; track_map = {'chords': 0}; current_track_index = 1
        if include_bass and self.generated_bass_midi_data: track_map['bass'] = current_track_index; num_tracks += 1; current_track_index += 1
        if include_arp and self.generated_arp_midi_data: track_map['arp'] = current_track_index; num_tracks += 1; current_track_index += 1
        if include_melody and self.generated_melody_midi_data: track_map['melody'] = current_track_index; num_tracks += 1; current_track_index += 1

        MyMIDI = MIDIFile(numTracks=num_tracks, removeDuplicates=False, deinterleave=False)
        chan = 0; start_time = 0;
        vol_chord=85; vol_arp=95; vol_bass=110; vol_melody=100;

        # --- Chords Track ---
        chord_track_idx = track_map['chords']
        # Use last_style_selection (Pool Style) for track name consistency
        chord_track_name = f"Chords ({self.last_generated_key} {self.last_style_selection})"
        MyMIDI.addTrackName(chord_track_idx, start_time, chord_track_name)
        if embed_tempo: MyMIDI.addTempo(chord_track_idx, start_time, bpm_value)

        time_cursor = start_time
        for i, (d_name, _, notes_for_midi, _, duration_beats) in enumerate(self.generated_chords_progression):
            if duration_beats <= 0: continue # Skip chords with no duration

            if isinstance(notes_for_midi, list) and notes_for_midi:
                 # Add chord name marker at the beginning of the chord's duration
                 MyMIDI.addText(chord_track_idx, time_cursor, d_name if d_name else "Chord")
                 # Add notes for the specified duration
                 note_start = time_cursor
                 # --- FIXED: Use full duration ---
                 actual_duration = duration_beats
                 for pitch in notes_for_midi:
                     if isinstance(pitch, int) and 0 <= pitch <= 127:
                         MyMIDI.addNote(chord_track_idx, chan, pitch, note_start, actual_duration, vol_chord)
            time_cursor += duration_beats # Increment time by the chord's duration

        # --- Other Tracks (Bass, Arp, Melody) ---
        # These lists already contain (pitch, absolute_start_time, duration, [velocity]) tuples
        if 'bass' in track_map:
            bass_track_idx = track_map['bass']
            bass_track_name = f"Bass ({self.last_generated_key} {self.last_style_selection})"
            MyMIDI.addTrackName(bass_track_idx, start_time, bass_track_name)
            for pitch, time, dur in self.generated_bass_midi_data:
                if isinstance(pitch, int) and 0 <= pitch <= 127 and dur > 0.01:
                     MyMIDI.addNote(bass_track_idx, chan, pitch, time, dur, vol_bass)

        if 'arp' in track_map:
            arp_track_idx = track_map['arp']
            arp_track_name = f"Arp ({self.last_generated_key} {self.last_style_selection})"
            MyMIDI.addTrackName(arp_track_idx, start_time, arp_track_name)
            for pitch, time, dur, vel in self.generated_arp_midi_data:
                if isinstance(pitch, int) and 0 <= pitch <= 127 and dur > 0.001:
                     MyMIDI.addNote(arp_track_idx, chan, pitch, time, dur, vel)

        if 'melody' in track_map:
            melody_track_idx = track_map['melody']
            melody_track_name = f"Melody ({self.last_generated_key} {self.last_style_selection} {melody_style} {melody_speed})"
            MyMIDI.addTrackName(melody_track_idx, start_time, melody_track_name)
            for pitch, time, dur in self.generated_melody_midi_data:
                if isinstance(pitch, int) and 0 <= pitch <= 127 and dur > 0.001:
                     MyMIDI.addNote(melody_track_idx, chan, pitch, time, dur, max(0, min(127, vol_melody + random.randint(-5, 5))))

        # --- Write File ---
        try:
            with open(output_path, "wb") as output_file: MyMIDI.writeFile(output_file)
            # print(f"Success: Wrote MIDI to {output_path}");
            return os.path.basename(output_path)
        except Exception as e: raise RuntimeError(f"Failed write MIDI: {e}") from e


    def run_regenerate_selected_parts(self):
        """Regenerates only the selected Arp, Melody, or Bass part and makes ONLY that part draggable."""
        if not self.generated_chords_progression:
            self.show_warning_message("Warning", "Generate full sequence first."); return
        if not self.save_directory and not self._get_save_directory():
            self.show_error_message("Save Error", "Need save directory."); return

        part_to_regen = self.regenerate_part_combo.currentText()
        if hasattr(self, 'chord_display_label'): self.chord_display_label.setText(f"(Regenerating {part_to_regen}...)")
        # Clear piano roll before regen (it will be repopulated later)
        if hasattr(self, 'piano_roll_widget'):
            self.piano_roll_widget.set_data([], [], [], [], 16.0)


        try:
            self.set_button_state(self.regenerate_button, False, "Regen..."); self.set_button_state(self.generate_button, False)
            self.update_status(f"Regenerating {part_to_regen}..."); self.update_drag_label(None)

            # Get current settings needed for the part
            arp_style_sel = self.arp_style_combo.currentText(); arp_octave_sel = self.arp_octave_combo.currentText()
            melody_style_sel = self.melody_style_combo.currentText(); melody_speed_sel = self.melody_speed_combo.currentText()
            melody_octave_sel = self.melody_octave_combo.currentText(); melody_gen_style_sel = self.melody_gen_style_combo.currentText()
            melody_instrument_sel = self.melody_instrument_combo.currentText() if hasattr(self, 'melody_instrument_combo') else MELODY_INSTRUMENT_OPTIONS[0]
            bass_style_sel = self.bass_style_combo.currentText() if hasattr(self, 'bass_style_combo') else BASS_STYLE_OPTIONS[0]

            bpm = self.bpm_spinbox.value(); embed_t = self.embed_tempo_check.isChecked()
            pool_style = self.last_style_selection # Use the pool style used for the chords

            # Get key info from last generation
            if not self.last_generated_key or not self.last_generated_key_type: raise RuntimeError("Missing key/type info for regeneration.")
            last_key = self.last_generated_key; last_type = self.last_generated_key_type
            is_minor = (last_type == "minor")
            root_name = last_key[:-1] if is_minor and last_key.endswith('m') else last_key
            if root_name not in ROOT_NOTES_MIDI: raise RuntimeError(f"Invalid last key root '{root_name}' stored.")
            root_midi = ROOT_NOTES_MIDI[root_name]
            scale_notes = get_natural_minor_scale_notes(root_midi) if is_minor else get_major_scale_notes(root_midi)
            if not scale_notes: raise RuntimeError("Failed to generate scale notes for regeneration.")

            regen_data = []; regen_name = ""; track_suffix = ""; vol = 100
            self.generation_count += 1
            single_part_out_path = None # Path for the single part MIDI file

            # Generate base filename (use last generated or create a fallback)
            base_name = self.last_generated_filename_base
            if not base_name:
                 prog_style_combo = self.prog_style_combo.currentText() if hasattr(self, 'prog_style_combo') else "Unknown"
                 prog_tag = f"_{prog_style_combo.split(' ')[0]}"
                 base_name = f"{self.last_generated_key.replace(' ', '_')}{prog_tag}_{self.last_generated_num_bars}B"

            if part_to_regen == "Arp":
                self.update_status("Regenerating Arp..."); self.generated_arp_midi_data = []
                self._generate_arpeggio(arp_style_sel, arp_octave_sel, scale_notes)
                regen_data = self.generated_arp_midi_data; regen_name = "Arp"; track_suffix = f"Regenerated Arp ({last_key})"; vol = 95
                if not regen_data: self.show_warning_message("Regen Warning", "Arp generation produced no notes.")
                else:
                    # --- FIX: Write ONLY the Arp part to a separate file ---
                    out_fname_single = f"{base_name}_{regen_name}_SINGLE_Regen_{self.generation_count}.mid"
                    out_path_single = os.path.join(self.save_directory, out_fname_single)
                    single_part_out_path = self._execute_write_single_part_midi(out_path_single, track_suffix, regen_data, "Arp", vol, bpm, embed_t)
                    # --- END FIX ---

            elif part_to_regen == "Melody":
                self.update_status("Regenerating Melody..."); self.generated_melody_midi_data = []
                melody_func_map = {
                    "Chord Tone Focus": generate_melody_chord_focus,
                    "Scale Walker": generate_melody_scale_walker,
                    "Experimental": generate_melody_experimental,
                    "Leaps & Steps": generate_melody_leaps_steps,
                    "Minimalist": generate_melody_minimalist,
                    "Sustained Lead": generate_melody_sustained_lead,
                }
                melody_func = melody_func_map.get(melody_gen_style_sel)
                if melody_gen_style_sel == "Random Style":
                    valid_funcs = [f for name, f in melody_func_map.items() if callable(f)]
                    if not valid_funcs: raise RuntimeError("No valid melody functions found for Random Style.")
                    melody_func = random.choice(valid_funcs)
                elif not melody_func or not callable(melody_func):
                    print(f"Warning: Melody function for '{melody_gen_style_sel}' not found or not callable. Using Chord Tone Focus.")
                    melody_func = generate_melody_chord_focus

                regen_data = melody_func(self.generated_chords_progression, scale_notes, melody_style_sel, melody_speed_sel, melody_octave_sel, melody_instrument_sel) # Pass instrument
                self.generated_melody_midi_data = regen_data; regen_name = "Melody"; track_suffix = f"Regenerated Melody ({last_key})"; vol = 100
                if not regen_data: self.show_warning_message("Regen Warning", "Melody generation produced no notes.")
                else:
                    # --- FIX: Write ONLY the Melody part to a separate file ---
                    out_fname_single = f"{base_name}_{regen_name}_SINGLE_Regen_{self.generation_count}.mid"
                    out_path_single = os.path.join(self.save_directory, out_fname_single)
                    single_part_out_path = self._execute_write_single_part_midi(out_path_single, track_suffix, regen_data, "Melody", vol, bpm, embed_t)
                    # --- END FIX ---

            elif part_to_regen == "Bass":
                 self.update_status("Regenerating Bass..."); self.generated_bass_midi_data = []
                 bass_func_map = {
                    "Standard": generate_bass_standard,
                    "Walking (Jazz)": generate_bass_walking,
                    "Pop": generate_bass_pop,
                    "RnB": generate_bass_rnb,
                    "Hip Hop": generate_bass_hip_hop,
                    "808": generate_bass_808
                 }
                 bass_func = bass_func_map.get(bass_style_sel, generate_bass_standard)
                 if bass_style_sel == "Walking (Jazz)":
                     self.generated_bass_midi_data = bass_func(self.generated_chords_progression, scale_notes)
                 else:
                     self.generated_bass_midi_data = bass_func(self.generated_chords_progression, scale_notes)

                 regen_data = self.generated_bass_midi_data; regen_name = "Bass"; track_suffix = f"Regenerated Bass ({last_key} {bass_style_sel})"; vol = 110
                 if not regen_data: self.show_warning_message("Regen Warning", "Bass generation produced no notes.")
                 else:
                    # --- FIX: Write ONLY the Bass part to a separate file ---
                    out_fname_single = f"{base_name}_{regen_name}_SINGLE_Regen_{self.generation_count}.mid"
                    out_path_single = os.path.join(self.save_directory, out_fname_single)
                    single_part_out_path = self._execute_write_single_part_midi(out_path_single, track_suffix, regen_data, "Bass", vol, bpm, embed_t)
                    # --- END FIX ---


            # --- FIX: Removed the call to write the combined MIDI file ---
            # self._execute_write_midi_file(
            #     out_path, include_arp, include_melody, include_bass,
            #     melody_style_sel, melody_speed_sel, bpm, embed_t
            # )


            # --- Update Piano Roll with current full state ---
            if hasattr(self, 'piano_roll_widget'):
                total_beats = self.last_generated_num_bars * 4.0
                # Get current checkbox state for display
                include_arp_disp = self.include_arp_check.isChecked()
                include_melody_disp = self.include_melody_check.isChecked()
                include_bass_disp = self.include_bass_check.isChecked()
                # FIX: Always pass generated chords if regeneration was successful
                self.piano_roll_widget.set_data(
                    self.generated_chords_progression, # Always pass chords
                    self.generated_arp_midi_data if include_arp_disp else [],
                    self.generated_bass_midi_data if include_bass_disp else [],
                    self.generated_melody_midi_data if include_melody_disp else [],
                    total_beats
                )

            # --- Update Status and Drag Label (point to the SINGLE part file if created) ---
            if single_part_out_path:
                try: # Display relative path
                     home = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.HomeLocation) or os.path.expanduser("~")
                     disp_fldr = os.path.relpath(self.save_directory, home)
                     if not disp_fldr.startswith(".."): disp_fldr = f"~{os.sep}{disp_fldr}"
                     else: disp_fldr = f"...{os.sep}{os.path.basename(self.save_directory)}"
                except Exception: disp_fldr = self.save_directory
                out_fname_display = os.path.basename(single_part_out_path)
                self.update_status(f"Success! Regenerated {regen_name}. Drag file:\n{out_fname_display}\n(Saved to {disp_fldr})")
                self.update_drag_label(single_part_out_path) # <-- Point drag label to single part file
            else:
                # Handle case where regeneration failed or produced no notes
                self.update_status(f"{regen_name} regenerated, but no notes produced or save failed.")
                self.update_drag_label(None)


            # --- MODIFIED: Chord Display Update on Regen ---
            if hasattr(self, 'chord_display_label') and self.generated_chords_progression:
                # Refresh chord display (it might have been overwritten during status updates)
                chord_names = [prog[0].split('/')[0] for prog in self.generated_chords_progression if prog[0]]
                # Get current chord rate setting for formatting
                chord_rate_sel = self.chord_rate_combo.currentText() if hasattr(self, 'chord_rate_combo') else "1 / Bar"
                current_prog_style = self.prog_style_combo.currentText() if hasattr(self, 'prog_style_combo') else PROG_STYLE_OPTIONS[0]
                is_blues = current_prog_style == "Blues (12 Bar)"
                display_limit = 16
                display_text = ""
                num_chords = len(chord_names)

                if chord_rate_sel == "1 / Bar" or is_blues:
                    display_text = " | ".join(chord_names[:display_limit])
                    if num_chords > display_limit: display_text += " | ..."
                else: # 2 / Bar
                    grouped = [" ".join(chord_names[i:i+2]) for i in range(0, num_chords, 2)]
                    limit_bars = display_limit // 2
                    display_text = " | ".join(grouped[:limit_bars])
                    if num_chords > display_limit : display_text += " | ..."
                self.chord_display_label.setText(f"Progression: {display_text}")
            # --- END MODIFIED Chord Display ---

        except RuntimeError as rterr:
            print(f"Runtime ERR regen: {rterr}"); traceback.print_exc(); self.show_error_message("Regen Error", f"{rterr}"); self.update_status(f"Error regenerating {part_to_regen}."); self.update_drag_label(None) # Clear drag label
            if hasattr(self, 'chord_display_label'): self.chord_display_label.setText("(Regen Failed)")
            if hasattr(self, 'piano_roll_widget'): self.piano_roll_widget.set_data([],[],[],[], 16.0) # Clear piano roll
        except Exception as e:
            print(f"ERR regen: {e}"); traceback.print_exc(); self.show_error_message("Error", f"Unexpected regeneration error:\n{e}"); self.update_status(f"Error regenerating {part_to_regen}."); self.update_drag_label(None) # Clear drag label
            if hasattr(self, 'chord_display_label'): self.chord_display_label.setText("(Regen Failed)")
            if hasattr(self, 'piano_roll_widget'): self.piano_roll_widget.set_data([],[],[],[], 16.0) # Clear piano roll
        finally: self.set_button_state(self.regenerate_button, True, "Regenerate Part"); self.set_button_state(self.generate_button, True)


    def _execute_write_single_part_midi(self, output_path, track_name, part_data, part_type, volume, bpm_value, embed_tempo):
        """Internal method to write a MIDI file containing only one part."""
        MyMIDI = MIDIFile(numTracks=1, removeDuplicates=False, deinterleave=False)
        chan = 0; start_time = 0
        MyMIDI.addTrackName(0, start_time, track_name)
        if embed_tempo: MyMIDI.addTempo(0, start_time, bpm_value)

        if part_type == "Arp":
            # Arp data: (pitch, time, dur, vel)
            for item in part_data:
                if len(item) == 4:
                    pitch, time, dur, vel = item
                    if isinstance(pitch, int) and 0<=pitch<=127 and dur>0.001: MyMIDI.addNote(0, chan, pitch, time, dur, vel)
        elif part_type == "Melody":
            # Melody data: (pitch, time, dur)
            for item in part_data:
                 if len(item) == 3:
                    pitch, time, dur = item
                    if isinstance(pitch, int) and 0<=pitch<=127 and dur>0.001: MyMIDI.addNote(0, chan, pitch, time, dur, max(0,min(127, volume + random.randint(-5,5))))
        elif part_type == "Bass":
             # Bass data: (pitch, time, dur)
             for item in part_data:
                 if len(item) == 3:
                     pitch, time, dur = item
                     if isinstance(pitch, int) and 0<=pitch<=127 and dur>0.01: MyMIDI.addNote(0, chan, pitch, time, dur, volume)
        try:
            with open(output_path, "wb") as out_f: MyMIDI.writeFile(out_f)
            # print(f"Success: Wrote single part MIDI: {output_path}");
            # Return the full path for the drag label
            return output_path
        except Exception as e: raise RuntimeError(f"Failed write single part MIDI for {part_type}: {e}") from e


    def run_randomize_all_options(self):
        """Randomly selects values for all GUI options."""
        # print("Randomizing options...")
        if self.style_combo.count() > 0: self.style_combo.setCurrentIndex(random.randint(0, self.style_combo.count() - 1))
        if random.choice([True, False]): self.major_radio.setChecked(True)
        else: self.minor_radio.setChecked(True)
        if self.key_root_combo.count() > 0: self.key_root_combo.setCurrentIndex(random.randint(0, self.key_root_combo.count() - 1))
        if self.num_bars_combo.isEnabled() and self.num_bars_combo.count() > 0:
             self.num_bars_combo.setCurrentIndex(random.randint(0, self.num_bars_combo.count() - 1))
        if self.complexity_combo.isEnabled() and self.complexity_combo.count() > 0:
             self.complexity_combo.setCurrentIndex(random.randint(0, self.complexity_combo.count() - 1))
        if self.bpm_spinbox.isEnabled(): self.bpm_spinbox.setValue(random.randint(60, 180))
        if self.embed_tempo_check.isEnabled(): self.embed_tempo_check.setChecked(random.choice([True, False]))

        # New Progression controls
        if hasattr(self, 'prog_style_combo') and self.prog_style_combo.count() > 0:
            self.prog_style_combo.setCurrentIndex(random.randint(0, self.prog_style_combo.count() - 1))
        if hasattr(self, 'chord_rate_combo') and self.chord_rate_combo.isEnabled() and self.chord_rate_combo.count() > 0:
            self.chord_rate_combo.setCurrentIndex(random.randint(0, self.chord_rate_combo.count() - 1))
        if hasattr(self, 'voicing_style_combo') and self.voicing_style_combo.isEnabled() and self.voicing_style_combo.count() > 0:
            self.voicing_style_combo.setCurrentIndex(random.randint(0, self.voicing_style_combo.count() - 1))
        if hasattr(self, 'cadence_combo') and self.cadence_combo.isEnabled() and self.cadence_combo.count() > 0:
            self.cadence_combo.setCurrentIndex(random.randint(0, self.cadence_combo.count() - 1))

        # Bass Style
        if hasattr(self, 'bass_style_combo') and self.bass_style_combo.isEnabled() and self.bass_style_combo.count() > 0:
            self.bass_style_combo.setCurrentIndex(random.randint(0, self.bass_style_combo.count() - 1))

        # Melody Instrument
        if hasattr(self, 'melody_instrument_combo') and self.melody_instrument_combo.isEnabled() and self.melody_instrument_combo.count() > 0:
             self.melody_instrument_combo.setCurrentIndex(random.randint(0, self.melody_instrument_combo.count() - 1))


        # Other controls
        if hasattr(self, 'chord_bias_combo') and self.chord_bias_combo.isEnabled() and self.chord_bias_combo.count() > 0:
             self.chord_bias_combo.setCurrentIndex(random.randint(0, self.chord_bias_combo.count() - 1))
        if self.arp_style_combo.isEnabled() and self.arp_style_combo.count() > 0:
             self.arp_style_combo.setCurrentIndex(random.randint(0, self.arp_style_combo.count() - 1))
        if self.arp_octave_combo.isEnabled() and self.arp_octave_combo.count() > 0:
             self.arp_octave_combo.setCurrentIndex(random.randint(0, self.arp_octave_combo.count() - 1))
        if self.melody_gen_style_combo.isEnabled() and self.melody_gen_style_combo.count() > 0:
             self.melody_gen_style_combo.setCurrentIndex(random.randint(0, self.melody_gen_style_combo.count() - 1))
        if self.melody_octave_combo.isEnabled() and self.melody_octave_combo.count() > 0:
             self.melody_octave_combo.setCurrentIndex(random.randint(0, self.melody_octave_combo.count() - 1))
        if self.melody_style_combo.isEnabled() and self.melody_style_combo.count() > 0:
             self.melody_style_combo.setCurrentIndex(random.randint(0, self.melody_style_combo.count() - 1))
        if self.melody_speed_combo.isEnabled() and self.melody_speed_combo.count() > 0:
             self.melody_speed_combo.setCurrentIndex(random.randint(0, self.melody_speed_combo.count() - 1))
        if self.include_arp_check.isEnabled(): self.include_arp_check.setChecked(random.choice([True, False]))
        if self.include_melody_check.isEnabled(): self.include_melody_check.setChecked(random.choice([True, False]))
        if self.include_bass_check.isEnabled(): self.include_bass_check.setChecked(random.choice([True, False]))
        if self.regenerate_part_combo.isEnabled() and self.regenerate_part_combo.count() > 0:
             self.regenerate_part_combo.setCurrentIndex(random.randint(0, self.regenerate_part_combo.count() - 1))

        self.update_status("Options randomized!"); self.update_drag_label(None)
        # Update UI based on potentially changed progression style
        self._update_ui_for_style(self.prog_style_combo.currentText())
        if hasattr(self, 'chord_display_label'): self.chord_display_label.setText("")
        # Clear piano roll on randomize
        if hasattr(self, 'piano_roll_widget'):
            self.piano_roll_widget.set_data([], [], [], [], 16.0)


# --- Application Entry Point ---
if __name__ == '__main__':
    # --- Changed Application Name and Version ---
    QCoreApplication.setApplicationName("Chorgi Version 0.7.1") # Incremented Version slightly
    QCoreApplication.setApplicationVersion("0.7.1")

    app = QApplication(sys.argv)

    # Set application style hints for potentially better tooltip behavior
    app.setStyle("Fusion") # Fusion style often has more consistent behavior across platforms

    # <<< MODIFIED ICON LOADING >>>
    # Use the helper function to find the icon path, relative to the bundle
    icon_path = resource_path(os.path.join('icons', 'chorgi_icon.png'))

    if os.path.exists(icon_path):
         app_icon = QIcon(icon_path)
         app.setWindowIcon(app_icon)
         # print(f"DEBUG: Set window icon from: {icon_path}")
    else:
         # Keep the fallback, but add a warning in case bundling went wrong
         print(f"WARNING: Custom icon not found at expected bundled path: {icon_path}. Using default.")
         # print(f"DEBUG: Custom icon not found. Using default.") # Original debug message
         app.setWindowIcon(QIcon.fromTheme("multimedia-audio-player", QIcon.fromTheme("audio-midi", QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-open-32.png"))))
    # <<< END MODIFIED ICON LOADING >>>

    window = ChorgiWindow()
    window.show()
    # print("DEBUG: Entering main event loop (app.exec())...")
    try:
        exit_code = app.exec()
        # print(f"DEBUG: Exited main event loop with code: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"ERROR in main application loop: {e}")
        traceback.print_exc()
        try:
            # Attempt to show error box even if main loop fails
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Icon.Critical); error_box.setWindowTitle("Application Error")
            error_box.setText(f"A critical error occurred:\n{e}\n\nPlease see the console output for details.")
            error_box.exec()
        except Exception as e2: print(f"Could not display final error message box: {e2}")
        sys.exit(1)
