#!/usr/bin/env python

__author__ = "Clemens Horch"
__copyright__ = "Copyright 2015, Clemens Horch"
__license__ = "MIT"
__email__ = "mail@clemenshorch.de"

import re
import os
import sys
import codecs

class ConAn:
	def __init__(self, label, linelength):
		self.linelength = linelength
		self.longestspeaker = ''
		self.turns = []
		self.output = ''
		self.label = label
		self.lastspeaker = ''
		self.linecount = 0
		self.has_marker = False
		self.linenumber = 0
		self.firstline = 0

	def tlen(self, text):
		return len(text.replace('>>', ''))

	def is_empty(self, text):
		text = text.replace('=', '')
		text = re.sub('\s\s+', ' ', text)
		text = text.strip()
		return text == ''

	def getbracket(self, idx):
		if idx == 0:
			return ''
		elif idx % 2 == 1:
			return '['
		else:
			return ']'

	def output_alone(self, speaker, text):
		if self.is_empty(text):
			return

		if speaker == self.lastspeaker:
			speaker = ''
		else:
			self.lastspeaker = speaker
		self.output += '\t\\alone{' + speaker + '}{'+ text.strip() + '}\n'
		self.linecount += 1

	def output_simul(self, As, At, Bs, Bt):
		if self.is_empty(At):
			self.output_alone(Bs, Bt)
		elif self.is_empty(Bt):
			self.output_alone(As, At)
		else:
			if As == self.lastspeaker:
				As = ''
			else:
				self.lastspeaker = As

			At = re.sub('\s\s+', ' ', At.strip())
			Bt = re.sub('\s\s+', ' ', Bt.strip())
			self.output += '\t\simul{' + As + '}{' + At + '}{' + Bs + '}{' + Bt + '}\n'
			self.linecount += 2
			
	def append(self, txt):
		# process lines
		for line in txt.splitlines():
			self.linenumber += 1

			# remove empty lines
			if line.strip() == '':
				continue

			# handle command lines
			if line[0] == '#':
				self.handle_command(line)
				continue

			# check if line has correct syntax 'speaker:text'
			if ':' not in line:
				print "Error at line {:}: no ':' found, skipping line".format(self.linenumber)
				continue

			#split speaker and text
			speaker, text =  line.split(':', 1)
			speaker = speaker.strip()

			# find longest speaker name
			if len(speaker) > len(self.longestspeaker):
				self.longestspeaker = speaker

			# search for marker sign
			if '>>' in text:
				self.has_marker = True

			# split into overlap groups
			text = text.strip()
			groups = re.split('[\[\]]', text)

			self.turns.append({'line':self.linenumber, 'speaker':speaker, 'text':text, 'groups':groups})

	def handle_command(self, line):
		if not '=' in line:
			print "Error at line {:}: no '=' found".format(self.linenumber)

		# split command name and value
		cmd = line[1:].split('=')

		if cmd[0] == 'line':
			if not cmd[1].isdigit():
				print "Error at line {:}: invalid value '{:}'".format(self.linenumber, cmd[1])
				return	
			self.firstline = int(cmd[1])
		else:
			print "Error at line {:}: unknown command '{:}'".format(self.linenumber, cmd[0])

	def process(self):
		textlen = self.linelength - len(self.longestspeaker) - 2

		turns_iter = enumerate(self.turns)
		for tidx, turn in turns_iter:
			self.lastspeaker = ''

			# error checking
			if len(turn['groups']) > 1 and tidx + 1 >= len(self.turns):
				print "Error at line {:}: last line in file with beginning overlap pair".format(turn['line'])
				turn['groups'] = [turn['text']]

			if len(turn['groups']) > 1 and len(turn['groups']) != len(self.turns[tidx + 1]['groups']):
				print "Error at line {:}: number of overlap pairs does not match line {:}".format(turn['line'], self.turns[tidx + 1]['line'])
				turn['groups'] = [turn['text']]

			# no overlap
			if len(turn['groups']) == 1:
				words = turn['text'].split()
				text = ''
				while len(words) > 0:
					if self.tlen(text) + self.tlen(words[0]) > textlen:
						self.output_alone(turn['speaker'], text)
						text = ''

					if len(words) > 0:
						text += words.pop(0) + ' '

				self.output_alone(turn['speaker'], text)
				continue

			# overlap
			A = turn
			B = self.turns[tidx + 1]
			Ao = ''
			Bo = ''

			# loop over all overlap groups
			for i,_ in enumerate(A['groups']):
				A['groups'][i] = self.getbracket(i) + A['groups'][i]
				B['groups'][i] = self.getbracket(i) + B['groups'][i]
				chunkA = A['groups'][i].split()
				chunkB = B['groups'][i].split()

				# loop over all words in a overlap group
				while(len(chunkA) > 0 or len(chunkB) > 0):
					# get next word
					nextA = ''
					nextB = ''
					if len(chunkA) > 0:
						nextA = chunkA[0]
					if len(chunkB) > 0:
						nextB = chunkB[0]

					#  flush line, if too long
					if self.tlen(Ao) + self.tlen(nextA) > textlen or self.tlen(Bo) + self.tlen(nextB) > textlen:
						Ao_new = ''
						Bo_new = ''
						if self.tlen(Ao) + self.tlen(nextA) > textlen and Bo.strip() != '':
							Ao += '='
							Ao_new = '= '		
						if self.tlen(Bo) + self.tlen(nextB) > textlen and Ao.strip() != '':
							Bo += '='
							Bo_new = '= '
						
						self.output_simul(A['speaker'], Ao, B['speaker'], Bo)				
						Ao = Ao_new
						Bo = Bo_new

					# append next word to line
					if len(chunkA) > 0:
						Ao += chunkA.pop(0) + ' '
						
					if len(chunkB) > 0:
						Bo += chunkB.pop(0) + ' '

					# align both lines with spaces before next group starts
					if len(chunkA) == 0:
						Ao += ' ' * (self.tlen(Bo) - self.tlen(Ao))
					if len(chunkB) == 0:
						Bo += ' ' * (self.tlen(Ao) - self.tlen(Bo))

			# output remaining buffer content				
			self.output_simul(A['speaker'], Ao, B['speaker'], Bo)

			# skip next turn
			next(turns_iter, None)

		header = ''
		if self.firstline > 0:
			header = '\\setcounter{conanline}{' + str(self.firstline) + '}\n'
		if self.firstline > self.linecount:
			self.linecount = self.firstline + self.linecount
		header += '\\begin{conan}['
		header += 'speaker=' + self.longestspeaker
		header += ',maxline=' + str(self.linecount)
		if self.has_marker:
			header += ',marker'
		header += ']\n'
		self.output = header + self.output
		if self.label:
			self.output += '\t\label{' + self.label + '}\n'
		self.output += '\end{conan}\n'

def process_file(filename, linelength):
	label = filename.replace(os.path.sep, '.')
	label = label.replace('..', '', 1)

	conan = ConAn(label, linelength)

	with codecs.open(filename, encoding='utf-8', mode='rb') as f:
		conan.append(f.read())

	print 'processing ' + filename
	conan.process()
	#print(conan.output)

	with codecs.open(filename + '.tex', encoding='utf-8', mode='wb') as f:
		f.write(conan.output)


if __name__ == "__main__":
	linelength = 64
	
	if len(sys.argv) > 1:
		linelength = int(sys.argv[1])
	else:
		print 'no linewidth specified, assuming ' + str(linelength)

	for root, dir, files in os.walk(u'.'):
		for f in files:
			name = os.path.join(root, f)
			if not name.endswith('.conan'):
				continue
			process_file(name, linelength)

