from build_dataset import filename, coefficients, to_midi, merge, to_3_str, to_events
import shutil
import json
from mido import MidiFile

json_path = 'parameters.json'
with open(json_path, 'r') as params_file:
    args = json.load(params_file)
output_dir = args["output_dir"]
phrases = {}
sorted_phrases = {}
melody = {}
for coef in coefficients:
    melody[coef] = []
    sorted_phrases[coef] = []
    phrases[coef] = []
for i in range(1, 910):
    variations_levenshtein = {}
    variations_sorted_levenshtein = {}
    variatons_levenshtein_melody = {}
    max_section = 0
    for coef in coefficients:
        variations_levenshtein[coef] = []
        variations_sorted_levenshtein[coef] = []
        variatons_levenshtein_melody[coef] = []
        with open(filename(output_dir, i, str(coef) + "/melody_levenshtein/pairs", ".txt"), 'r') as f:
            for line in f.readlines():
                variatons_levenshtein_melody[coef].append([int(x) for x in line.split()])
                max_section = max(max_section, max(variatons_levenshtein_melody[coef][-1]))
        with open(filename(output_dir, i, str(coef) + "/sections_levenshtein/pairs", ".txt"), 'r') as f:
            for line in f.readlines():
                variations_levenshtein[coef].append([int(x) for x in line.split()])
                max_section = max(max_section, max(variations_levenshtein[coef][-1]))
        with open(filename(output_dir, i, str(coef) + "/sorted_sections_levenshtein/pairs", ".txt"), 'r') as f:
            for line in f.readlines():
                variations_sorted_levenshtein[coef].append([int(x) for x in line.split()])
                max_section = max(max_section, max(variations_sorted_levenshtein[coef][-1]))

    all_events = []
    for k in range(max_section + 1):
        midi = MidiFile(filename(output_dir, i, to_3_str(i) + '_section_' + str(k)), clip=True)
        all_events.append([{}, 0])
        for track in midi.tracks:
            all_events[-1][0][track.name] = to_events(track)

    for ind1, e1 in enumerate(all_events):
        for ind2, e2 in enumerate(all_events):
            is_written = ''
            for coef in coefficients:
                flag = False
                if [ind1, ind2] in variatons_levenshtein_melody[coef]:
                    flag = True
                    path = filename(output_dir, i, str(coef) + "/" + "melody_levenshtein" + "/" + to_3_str(i) + "_" + str(ind1) + "-" + str(ind2), ".midi")
                    if is_written != '':
                        shutil.copy2(is_written, path) 
                    else:
                        tmp = to_midi(merge(e1, e2))
                        tmp.save(path)
                    is_written = path
                    melody[coef].append([ind1, ind2])
                if [ind1, ind2] in variations_sorted_levenshtein[coef]:
                    flag = True
                    path = filename(output_dir, i, str(coef) + "/" + "sorted_sections_levenshtein" + "/" + to_3_str(i) + "_" + str(ind1) + "-" + str(ind2), ".midi")
                    if is_written != '':
                        shutil.copy2(is_written, path) 
                    else:
                        tmp = to_midi(merge(e1, e2))
                        tmp.save(path)
                    is_written = path
                    sorted_phrases[coef].append([ind1, ind2])
                if [ind1, ind2] in variations_levenshtein[coef]:
                    flag = True
                    path = filename(output_dir, i, str(coef) + "/" + "sections_levenshtein" + "/" + to_3_str(i) + "_" + str(ind1) + "-" + str(ind2), ".midi")
                    if is_written != '':
                        shutil.copy2(is_written, path) 
                    else:
                        tmp = to_midi(merge(e1, e2))
                        tmp.save(path)
                    is_written = path
                    phrases[coef].append([ind1, ind2])
                if not flag:
                    break
    if i % 1 == 0:
        print(str(int(i)) + "%")
for c in coefficients:
    print(c, "melody:", len(melody[c]), "phrases:", len(phrases[c]), "sorted_phrases:", len(sorted_phrases[c]), melody[c] == phrases[c], phrases[c] == sorted_phrases[c], melody[c] == sorted_phrases[c])
