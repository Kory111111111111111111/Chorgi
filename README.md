# Chorgi - MIDI Music Generator


## Important Announcement: 

![image](https://github.com/user-attachments/assets/ddf44a68-817a-4631-b0c3-0d3d5228cfe1) I am still in the process of converting Chorgi to C++ on the JUCE framework. Please bear in mind this is not an easy task for me and is going to take a significant ammount of time, I would not be doing this if I did not truly belive that this is a neccesarry step for the Plugins success. 




## Description

Chorgi is a desktop application for Windows, developed by an individual driven by a passion for music and creating tools to facilitate the music creation process. It offers a graphical interface for users to automatically generate MIDI music compositions, with controls for various parameters across chord progressions, arpeggios, melodies, and basslines.

## Known Issues 

* Currently when you generate MIDI there is a chance that the piano roll may not show the notes in the correct color in which they represent. Bass notes are also being cutoff by the bottom of the piano roll on occasion, this is caused by me readjusting the overall size of the piano roll and not properly adjusting how the piano roll figures out how to organize all notes inside of it.

* Piano roll still cannot be chagned, this is a very complex thing for me and I am already struggling to get it to work the way it does now, I will be implemnting an editable Pian Roll in due time. 

* Program is standalone and cannot be loaded into a DAW. As said before, it still functions as a VST3 does, you just need to run open it outside of your DAW. Once I have verified all the features work as expected without bugs I will at that point start the conversion to C and wrap it into VST3, AUv3, and CLAP (as long as it becomes more widely adopted)

* The "Triplet Feel" Melody Algorhytm currently produces shit. That is the best way to put it, it is no longer entirely random, but it still sounds like shit which is not the intended behavior. I am actively working on updating this and will implement it in due time.

## Download

You can download the latest executable version of Chorgi from the [Releases page](https://github.com/Kory111111111111111111/Chorgi/releases/tag/Downloads).

## Features

* **Graphical User Interface:** Easy-to-use interface built with PyQt6.
* **Key Selection:** Choose the root note and whether the key is major or minor.
* **Chord Generation:**
    * **Pool Styles:** Select between 'Chorgi' (standard diatonic) and 'Jazzy' chord voicings/extensions. Chord pools now include `sus2`, `sus4`, `maj6`, and `m6` chords.
    * **Progression Styles:** Generate progressions based on templates like 'Pop (I-V-vi-IV)', 'Blues (12 Bar I-IV-V)', 'Rock (I-IV-V)', 'Jazz (ii-V-I)', 'Folk (I-IV-V-I)', 'Minor Ballad (i-VII-VI-i)', 'R&B/Soul (I-vi-ii-V)', or use a 'Smooth Random' algorithm.
    * **Customization:** Adjust chord complexity (Standard Triads/7ths or Extra Extensions), chord rate (1 or 2 per bar), voicing style (Root Position, Allow Inversions, Prefer Drop 2, Quartal, So What), cadence preference (Any, Authentic V-I, Plagal IV-I), and harmonic bias (Standard, Darker, Lighter).
* **Arpeggiator:**
    * **Patterns:** Multiple arpeggio patterns (Random Consistent, Random per Bar, Ascending, Descending, Up-Down, Random Notes, Converge/Diverge).
    * **Rhythm:** Selectable base note values (1/4, 1/8, 1/16 Note) with an option for a Triplet Modifier.
    * **Range:** Control the octave range relative to the chord (Original, +/- 1 Octave, +/- 2 Octaves, +/- 3 Octaves).
* **Melody Generation:**
    * **Algorithms:** Various generation styles like 'Chord Tone Focus', 'Scale Walker', 'Experimental', 'Leaps & Steps', 'Minimalist', 'Sustained Lead', 'Triplet Feel', or 'Random Style'.
    * **Customization:** Control melody articulation (Legato/Staccato), speed (Slow/Medium/Fast), and octave range (Mid/High).
    * **Instrument Hint:** Select a target instrument type (None, Synth Lead, Keys, Piano, Pluck) to subtly influence generation patterns.
* **Bassline Generation:**
    * **Styles:** Generate basslines in different styles: 'Standard', 'Walking (Jazz)', 'Pop', 'RnB', 'Hip Hop', '808'. The '808' style includes dynamic variations and pitch slides. Currently the 808 primarily tries to make "slide" patterns, use the "Hip Hop" generation algorithm for none slide 808 bass patterns.
* **Part Control:**
    * Independently include or exclude the Arpeggio, Melody, and Bassline parts from the final output.
    * Regenerate individual parts (Arp, Melody, Bass) without changing the others.
* **MIDI Output:**
    * Set the Beats Per Minute (BPM).
    * Option to embed the tempo information directly into the MIDI file.
    * Generated MIDI files are automatically saved to a dedicated folder (`Documents/Chorgi MIDI Files`).
    * **Drag and Drop:** Easily drag the generated MIDI file directly from the application into your Digital Audio Workstation (DAW) or file explorer.
* **Visualization & UI:**
    * Displays the generated chord progression names.
    * Includes a simple Piano Roll visualization of the generated notes (Chords, Bass, Arp, Melody). Notes are colored based on the part.
    * Features a Dark (Nord) UI theme.
    * "🎲" Randomize button to quickly set all options to random values.
    * Status bar for feedback during generation.

## Usage

1.  Run the downloaded executable file.
2.  Select the desired musical parameters using the dropdown menus, radio buttons, checkboxes, and spin boxes in the GUI.
3.  Click the "Generate MIDI" button.
4.  The application will generate the MIDI data based on your selections.
5.  The generated MIDI file will be automatically saved in your `Documents/Chorgi MIDI Files` directory. The filename and save location will be displayed in the status bar.
6.  You can click and drag the file path displayed in the "Drag:" label directly into your DAW or file explorer.
7.  Use the "Regenerate Part" section to regenerate only the Arp, Melody, or Bassline using the current settings. This will save a *new* MIDI file containing only the regenerated part.
8.  Use the "🎲" (Randomize) button to set all options to random values.

## Contact

Developed by Kory Drake. For support or feedback, contact: kory.drake207@gmail.com. Thank you to everyone who has helped thus far with testing.
