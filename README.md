# Chorgi - MIDI Music Generator

## Description

Chorgi is a desktop application built with Python and PyQt6 that allows users to generate MIDI music compositions. It provides a graphical user interface (GUI) to control various parameters for creating chord progressions, arpeggios, melodies, and basslines automatically. It can be downloaded here https://github.com/Kory111111111111111111/Chorgi/releases/tag/Downloads

## Features

* **Graphical User Interface:** Easy-to-use interface built with PyQt6.
* **Key Selection:** Choose the root note and whether the key is major or minor.
* **Chord Generation:**
    * **Pool Styles:** Select between 'Chorgi' (standard diatonic) and 'Jazzy' chord voicings/extensions.
    * **Progression Styles:** Generate progressions based on templates like 'Pop (I-vi-IV-V)', 'Pachelbel-ish', 'ii-V-I Focused', 'Minor Pop (i-VI-III-VII)', 'Folk Strum', '12 Bar Blues', or use a 'Smooth Random' algorithm.
    * **Customization:** Adjust chord complexity (triads/7ths or extensions), chord rate (1 or 2 per bar), voicing style (root position, inversions, Drop 2), cadence preference, and harmonic bias (standard, darker, lighter).
* **Arpeggiator:**
    * **Patterns:** Multiple arpeggio patterns (Ascending, Descending, Up-Down, Random Notes, Converge/Diverge, Random per Bar).
    * **Rhythm:** Selectable note values (1/4, 1/8, 1/16) with an option for triplet variations.
    * **Range:** Control the octave range relative to the chord.
* **Melody Generation:**
    * **Algorithms:** Various generation styles like 'Chord Tone Focus', 'Scale Walker', 'Experimental', 'Leaps & Steps', 'Minimalist', 'Sustained Lead', 'Triplet Feel', or 'Random Style'.
    * **Customization:** Control melody articulation (Legato/Staccato), speed (Slow/Medium/Fast), and octave range (Mid/High).
    * **Instrument Hint:** Select a target instrument type (Synth Lead, Keys, Piano, Pluck) to subtly influence generation.
* **Bassline Generation:**
    * **Styles:** Generate basslines in different styles: 'Standard', 'Walking (Jazz)', 'Pop', 'RnB', 'Hip Hop', '808'.
* **Part Control:**
    * Independently include or exclude the Arpeggio, Melody, and Bassline parts from the final output.
    * Regenerate individual parts (Arp, Melody, Bass) without changing the others.
* **MIDI Output:**
    * Set the Beats Per Minute (BPM).
    * Option to embed the tempo information directly into the MIDI file.
    * Generated MIDI files are automatically saved to a dedicated folder (`Documents/Chorgi MIDI Files`).
    * **Drag and Drop:** Easily drag the generated MIDI file directly from the application into your Digital Audio Workstation (DAW).
* **Visualization & UI:**
    * Displays the generated chord progression names.
    * Includes a simple Piano Roll visualization of the generated notes (Chords, Bass, Arp, Melody).
    * Features Dark and Light UI themes.
    * "Randomize" button to quickly generate new ideas.
    * Status bar for feedback during generation.

## Requirements

* Python 3.x
* PyQt6: `pip install PyQt6`
* midiutil: `pip install midiutil`

## Installation

1.  Ensure you have Python 3 installed.
2.  Install the required libraries:
    ```bash
    pip install PyQt6 midiutil
    ```
3.  Save the code as a Python file (e.g., `chorgi_app.py`).

## Usage

1.  Run the script from your terminal:
    ```bash
    python chorgi_app.py
    ```
    (Replace `chorgi_app.py` with the actual filename if you saved it differently).
2.  Select the desired musical parameters using the dropdown menus, radio buttons, checkboxes, and spin boxes in the GUI.
3.  Click the "Generate MIDI" button.
4.  The application will generate the MIDI data based on your selections.
5.  The generated MIDI file will be automatically saved in your `Documents/Chorgi MIDI Files` directory. The filename and save location will be displayed in the status bar.
6.  You can click and drag the file path displayed in the "Drag:" label directly into your DAW or file explorer.
7.  Use the "Regenerate Part" section to regenerate only the Arp, Melody, or Bassline using the current settings. This will save a *new* MIDI file containing only the regenerated part.
8.  Use the "🎲" (Randomize) button to set all options to random values.

## Contact

Developed by Kory Drake. For support or feedback, contact: kory.drake207@gmail.com. Thank you to everyone who has helped thus far with testing. As we get closer to release I will be removing the source and we will be utilizing a private solution to host test builds.

