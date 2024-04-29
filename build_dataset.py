import json
from mido import MidiFile, Message
import numpy
import random
from functools import cmp_to_key
import os

class Event:
    def __init__(self, global_time, message):
        self.global_time = global_time
        self.message = message
    def __repr__(self):
        return f"({self.global_time}, {self.message})"

def to_3_str(i):
    if type(i) == str:
        return i
    if i < 10:
        return '00' + str(i)
    if i < 100:
        return '0' + str(i)
    return str(i)

def filename(dir, n, file, extension=".mid"):
    return dir + to_3_str(n) + '/' + file + extension

def to_events(track):
    res = []
    current_time = 0
    for msg in track:
        current_time += msg.time
        if msg.type in ["track_name", "end_of_track"]:
            continue
        res.append(Event(current_time, msg))
    return res

def to_midi(tracks):
    midi = MidiFile()
    for track_name in tracks.keys():
        midi.add_track(track_name)
        last_event_time = 0
        for event in tracks[track_name]:
            event.message.time = event.global_time - last_event_time
            last_event_time = event.global_time
            midi.tracks[-1].append(event.message)
    return midi

def get_nth_note_event(track, i):
    for e in track:
        if e.message.type == 'note_on':
            if i == 0:
                return e
            i -= 1

def split(original_piece, split_time, add_left=False):
    left_piece = {}
    right_piece = {}
    
    for track_name in original_piece.keys():
        '''if track_name == '':
            left_piece[track_name] = original_piece[track_name]
            right_piece[track_name] = original_piece[track_name]
            
            """right_piece[track_name] = []
            for e in original_piece[track_name]:
                right_piece[track_name].append(Event(e.global_time + split_time, e.message))"""
            continue'''

        left_piece[track_name] = []
        right_piece[track_name] = []
        opened_note_on_events = []
        flag = False
        for event in original_piece[track_name]:
            if event.global_time >= split_time:
                if not flag:
                    for opened_note in opened_note_on_events:
                        right_piece[track_name].append(Event(split_time, opened_note.message))
                        left_piece[track_name].append(Event(split_time, Message('note_on', note=opened_note.message.note, channel=opened_note.message.channel, velocity=0, time=0)))
                    flag = True
            if event.message.type in ['note_on', 'note_off']:
                if event.global_time < split_time:
                    left_piece[track_name].append(event)
                    if event.message.velocity != 0:
                        opened_note_on_events.append(event)
                    else:
                        for opened_note in opened_note_on_events:
                            if (event.message.note == opened_note.message.note) and (event.message.channel == opened_note.message.channel):
                                opened_note_on_events.remove(opened_note)
                                break
                else:
                    right_piece[track_name].append(event)
            else:
                right_piece[track_name].append(Event(max(event.global_time, split_time), event.message))
                if event.global_time <= split_time:
                    left_piece[track_name].append(event)
    return left_piece, right_piece

length_of_16th = 120
signature_in_16th = 16

def min_time_of_piece(piece):
    cur_time = 1000000
    for track in piece.keys():
        a = get_nth_note_event(piece[track], 0)
        if a is not None:
            cur_time = min(cur_time, a.global_time)
    return cur_time

def max_time_of_piece(piece):
    cur_time = 0
    for track in piece.keys():
        a = get_nth_note_event(piece[track][::-1], 0)
        if a is not None:
            cur_time = max(cur_time, a.global_time)
    return cur_time

def get_melody(original_piece, i):
    melody = []
    cur_time = min_time_of_piece(original_piece)
    k = 0
    with open("POP909/" + to_3_str(i) + "/melody.txt", "r") as f:
        for l in f.readlines():
            a, b = l.split()
            a, b = int(a), int(b)
            if a == 0:
                cur_time += b * length_of_16th
                continue
            while k < len(original_piece["MELODY"]):
                e = original_piece["MELODY"][k]
                msg = e.message
                if (msg.type != "note_on") or (msg.velocity == 0):
                    if msg.type not in ["note_on", "note_off"]:
                        melody.append(Event(cur_time, msg))
                    k += 1
                    continue
                ch = msg.channel
                vel = msg.velocity
                k += 1
                break
            melody.append(Event(cur_time, Message("note_on", note=a, channel=ch, velocity=vel, time=0)))
            cur_time += b * length_of_16th
            melody.append(Event(cur_time, Message("note_on", note=a, channel=ch, velocity=0, time=0)))
        while k < len(original_piece["MELODY"]):
            e = original_piece["MELODY"][k]
            msg = e.message
            if msg.type not in ["note_on", "note_off"]:
                melody.append(Event(cur_time, msg))
            k += 1
    return sorted(melody, key=cmp_to_key(lambda x, y: x.global_time < y.global_time))

def is_melodic(phrase):
    return phrase_type(phrase).isupper()

def split_labeling(i):
    phrases = [""]
    lengths = []
    with open("POP909/" + to_3_str(i) + "/human_label1.txt", "r") as f:
        for line in f.readlines():
           c = 0
           if line[-1] == '\n':
               line = line[:-1]
           while c < len(line):
                phrases[-1] += line[c]
                c += 1
                while (c < len(line)) and (line[c].isdigit()):
                    phrases[-1] += line[c]
                    c += 1
                lengths.append(int(phrases[-1][1:]) * length_of_16th * signature_in_16th)
                phrases.append("")
    phrases.pop()
    sections = []
    i = 0
    while i < len(phrases):
        sum_length = 0
        section = []
        while (i < len(phrases)) and (is_melodic(phrases[i])):
            sum_length += lengths[i]
            section.append(phrases[i])
            i += 1
        if sum_length > 0:
            sections.append([section, sum_length])
        sum_length = 0
        section = []
        while (i < len(phrases)) and (not is_melodic(phrases[i])):
            sum_length += lengths[i]
            section.append(phrases[i])
            i += 1
        if sum_length > 0:
            sections.append([section, sum_length])
    return sections

def get_sections(original_piece, sections, only_melodic):
    cur_time = min_time_of_piece(original_piece)
    res = []
    for section, length in sections:
        if is_melodic(section):
            res.append([shift_to_0(split(split(original_piece, cur_time)[1], cur_time + length)[0]), section])
            cur_time += length
        else: 
            if not only_melodic:
                res.append([shift_to_0(split(split(original_piece, cur_time)[1], cur_time + length)[0]), section])
            cur_time += length
    return res

def section_levenshtein(section1, section2):
    distances = numpy.zeros((len(section1) + 1, len(section2) + 1))

    for t1 in range(1, len(section1) + 1):
        distances[t1][0] = distances[t1 - 1][0] + phrase_len(section1[t1 - 1])

    for t2 in range(1, len(section2) + 1):
        distances[0][t2] = distances[0][t2 - 1] + phrase_len(section2[t2 - 1])

    a = 0
    b = 0
    c = 0
    
    for t1 in range(1, len(section1) + 1):
        for t2 in range(1, len(section2) + 1):
            if (section1[t1 - 1] == section2[t2 - 1]):
                dist = 0
                if phrase_type(section1[t1 - 1]) == 'X':
                    dist = phrase_len(section1[t1 - 1])
                distances[t1][t2] = distances[t1 - 1][t2 - 1] + dist
            else:
                a = distances[t1][t2 - 1]
                b = distances[t1 - 1][t2]
                c = distances[t1 - 1][t2 - 1]
                
                if (a <= b and a <= c):
                    distances[t1][t2] = a + phrase_len(section1[t1 - 1])
                elif (b <= a and b <= c):
                    distances[t1][t2] = b + phrase_len(section2[t2 - 1])
                else:
                    if phrase_type(section1[t1 - 1]) == phrase_type(section2[t2 - 1]) and phrase_type(section2[t2 - 1]) != "X":
                        dist = abs(phrase_len(section1[t1 - 1]) - phrase_len(section2[t2 - 1]))
                    else:
                        dist = max(phrase_len(section1[t1 - 1]), phrase_len(section2[t2 - 1]))
                    distances[t1][t2] = c + dist

    return distances[len(section1)][len(section2)]

def phrase_len(phrase):
    p = "".join(list(filter(lambda c: c.isdigit(), phrase)))
    return int(p)

def phrase_type(phrase):
    p = "".join(list(filter(lambda c: not c.isdigit(), phrase)))
    return p

def section_len(section):
    return sum([phrase_len(p) for p in section])

coefficients = [0.1, 0.25, 0.5, 0.75, 0.9]

def get_levenshtein_variations(sections):
    res = {}
    for coef in coefficients:
        res[coef] = []
    for i in range(len(sections)):
        a = sections[i][0]
        if not is_melodic(a):
            continue
        for j in range(i + 1, len(sections)):
            b = sections[j][0]
            if not is_melodic(b):
                continue
            dist = section_levenshtein(a, b)
            for c in res.keys():
                if 1 - (dist / (max(section_len(a), section_len(b)))) >= c:
                    res[c].append([i, j])
    return res

def get_sorted_levenshtein_variations(sections):
    res = {}
    for coef in coefficients:
        res[coef] = []
    for i in range(len(sections)):
        a = sorted(sections[i][0])
        if not is_melodic(a):
            continue
        for j in range(i + 1, len(sections)):
            b = sorted(sections[j][0])
            if not is_melodic(b):
                continue
            dist = section_levenshtein(a, b)
            for c in res.keys():
                if 1 - (dist / max(section_len(a), section_len(b))) >= c:
                    res[c].append([i, j])
    return res

def get_sections_melody(sections_as_separated_pieces):
    res = [[] for _ in range(len(sections_as_separated_pieces))]
    for i, section in enumerate(sections_as_separated_pieces):
        first_event = get_nth_note_event(section[0]["MELODY"], 0)
        if first_event is None:
            continue
        last_time = first_event.global_time
        for event in section[0]["MELODY"]:
            if event.message.type not in ["note_on", "note_off"]:
                continue
            if event.message.velocity != 0:
                for _ in range((event.global_time - last_time) // length_of_16th):
                    res[i].append(0)
                last_time = event.global_time
                continue
            for _ in range((event.global_time - last_time) // length_of_16th):
                res[i].append(event.message.note)
            last_time = event.global_time
    return res

def levenshtein(section1, section2):
    distances = numpy.zeros((len(section1) + 1, len(section2) + 1))

    for t1 in range(1, len(section1) + 1):
        distances[t1][0] = t1

    for t2 in range(1, len(section2) + 1):
        distances[0][t2] = t2

    a = 0
    b = 0
    c = 0
    
    for t1 in range(1, len(section1) + 1):
        for t2 in range(1, len(section2) + 1):
            if (section1[t1 - 1] == section2[t2 - 1]):
                distances[t1][t2] = distances[t1 - 1][t2 - 1]
            else:
                a = distances[t1][t2 - 1]
                b = distances[t1 - 1][t2]
                c = distances[t1 - 1][t2 - 1]
                
                if (a <= b and a <= c):
                    distances[t1][t2] = a + 1
                elif (b <= a and b <= c):
                    distances[t1][t2] = b + 1
                else:
                    distances[t1][t2] = c + 1

    return distances[len(section1)][len(section2)]

def get_melody_levenshtein_variations(sections):
    res = {}
    for coef in coefficients:
        res[coef] = []
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            a, b = sections[i], sections[j]
            dist = levenshtein(a, b)
            for c in res.keys():
                if 1 - (dist / max(len(a), len(b))) >= c:
                    res[c].append([i, j])
    return res

def shift(events, time):
    res = {}
    for track in events.keys():
        res[track] = []
        for e in events[track]:
            res[track].append(Event(e.global_time + time, e.message))
    return res

def shift_to_0(events):
    time = min_time_of_piece(events)
    res = {}
    for track in events.keys():
        res[track] = []
        for e in events[track]:
            res[track].append(Event(max(e.global_time - time, 0), e.message))
    return res

def get_phrases(piece, section):
    res = []
    cur_time = min_time_of_piece(piece)
    piece = shift_to_0(piece)
    piece = shift(piece, cur_time)
    for phrase in section:
        duration = phrase_len(phrase) * length_of_16th * signature_in_16th
        cur = piece.copy()
        cur = split(split(cur, cur_time)[1], cur_time + duration)[0]
        for t in cur.keys():
            cur[t] = list(filter(lambda e: e.global_time <= cur_time + duration and e.global_time >= cur_time, cur[t]))
        cur = shift_to_0(cur)
        cur_time += duration
        res.append([phrase, cur])
    return res

def to_section(phrases_events):
    return [phrase for phrase, _ in phrases_events]

def shuffable(phrases_events):
    return len(list(set(to_section(phrases_events)))) > 1

def shuffle(sections_events):
    shuffled_phrases = []
    shuffled_events = []
    for piece, section in sections_events:
        phrases_events = get_phrases(piece, section)
        if shuffable(phrases_events):
            while True:
                random.shuffle(phrases_events)
                cur = to_section(phrases_events)
                if cur != section:
                    break
        else:
            continue
        shuffled_phrases.append([[], 0])
        cur = {}
        shift_time = 0
        for phrase, events in phrases_events:
            shuffled_phrases[-1][0].append(phrase)
            events = shift(events, shift_time)
            for track in events.keys():
                if track == '':
                    if cur == {}:
                        cur[''] = events['']
                    continue
                if track not in cur.keys():
                    cur[track] = []
                cur[track] += events[track]
            shift_time += phrase_len(phrase) * length_of_16th * signature_in_16th
        shuffled_events.append([cur, 0])
    return shuffled_events, shuffled_phrases

def merge(events1, events2):
    res = {}
    for e in events1[0].keys():
        res[e] = events1[0][e].copy()
    t = max([max(list(map(lambda e: e.global_time, events1[0][track])) if len(events1[0][track]) > 0 else [-1]) for track in events1[0].keys()])
    res["SEPARATOR"] = [Event(t, Message("note_on", note=0, velocity=1, channel=0, time=0)), 
                        Event(t + 1, Message("note_on", note=0, velocity=0, channel=0, time=0))]
    shifted = shift(events2[0], t + 1)
    for track in res.keys():
        if track in shifted.keys():
            res[track] += shifted[track]
    return res

def handle_dataset(create_dataset, input_midi_dir, output_dir):
    phrases = {}
    sorted_phrases = {}
    melody = {}
    for coef in coefficients:
        melody[coef] = []
        sorted_phrases[coef] = []
        phrases[coef] = []
    for i in range(1, 910):
        original_piece_midi = MidiFile(filename(input_midi_dir, i, to_3_str(i)), clip=True)
        
        original_piece = {}
        for track in original_piece_midi.tracks:
            original_piece[track.name] = to_events(track)
        
        original_piece["MELODY"] = get_melody(original_piece, i)

        sections = split_labeling(i)

        trimmed_piece = shift_to_0(split(split(original_piece, get_nth_note_event(original_piece["MELODY"][::-1], 0).global_time)[0], get_nth_note_event(original_piece["MELODY"], 0).global_time)[1])
        if not is_melodic(sections[0][0][0]):
            sections.pop(0)
        if not is_melodic(sections[-1][0][0]):
            sections.pop()

        sections_as_separated_pieces = get_sections(trimmed_piece.copy(), sections, True)
        shuffled_sections_events, shuffled_sections = shuffle(sections_as_separated_pieces)

        all_sections = list(filter(lambda x: is_melodic(x[0]), sections + shuffled_sections))
        all_events = sections_as_separated_pieces + shuffled_sections_events
        
        variations_levenshtein = get_levenshtein_variations(all_sections)
        variations_sorted_levenshtein = get_sorted_levenshtein_variations(all_sections)
        variatons_levenshtein_melody = get_melody_levenshtein_variations(get_sections_melody(all_events))

        if create_dataset:
            to_midi(original_piece).save(filename(output_dir, i, to_3_str(i)))
            to_midi(trimmed_piece).save(filename(output_dir, i, to_3_str(i) + '_trimmed'))
            for coef in coefficients:
                if not os.path.exists(filename(output_dir, i, str(coef), extension="/")):
                    os.makedirs(filename(output_dir, i, str(coef) + "/" + "sections_levenshtein", extension="/"))
                    os.makedirs(filename(output_dir, i, str(coef) + "/" + "sorted_sections_levenshtein", extension="/"))
                    os.makedirs(filename(output_dir, i, str(coef) + "/" + "melody_levenshtein", extension="/"))
                with open(filename(output_dir, i, str(coef) + "/melody_levenshtein/pairs", ".txt"), 'w') as f:
                    for pair in variatons_levenshtein_melody[coef]:
                        f.write(str(pair[0]) + " " + str(pair[1]) + '\n')
                        f.write(str(pair[1]) + " " + str(pair[0]) + '\n')
                        melody[coef].append(pair)
                        melody[coef].append(pair[::-1])
                with open(filename(output_dir, i, str(coef) + "/sections_levenshtein/pairs", ".txt"), 'w') as f:
                    for pair in variations_levenshtein[coef]:
                        f.write(str(pair[0]) + " " + str(pair[1]) + '\n')
                        f.write(str(pair[1]) + " " + str(pair[0]) + '\n')
                        phrases[coef].append(pair)
                        phrases[coef].append(pair[::-1])
                with open(filename(output_dir, i, str(coef) + "/sorted_sections_levenshtein/pairs", ".txt"), 'w') as f:
                    for pair in variations_sorted_levenshtein[coef]:
                        f.write(str(pair[0]) + " " + str(pair[1]) + '\n')
                        f.write(str(pair[1]) + " " + str(pair[0]) + '\n')
                        sorted_phrases[coef].append(pair)
                        sorted_phrases[coef].append(pair[::-1])
            for k, section in enumerate(all_events):
                to_midi(shift_to_0(section[0])).save(filename(output_dir, i, to_3_str(i) + '_section_' + str(k)))
            
        if i % 20 == 0:
            print(str(int(i / 910 * 100)) + "%")
    for c in coefficients:
        print(c, "melody:", len(melody[c]), "phrases:", len(phrases[c]), "sorted_phrases:", len(sorted_phrases[c]), melody[c] == phrases[c], phrases[c] == sorted_phrases[c], melody[c] == sorted_phrases[c])

def main():
    json_path = 'parameters.json'
    with open(json_path, 'r') as params_file:
        args = json.load(params_file)
    handle_dataset(**args)

if __name__ == '__main__':
    main()