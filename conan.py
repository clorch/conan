#!/usr/bin/env python

__author__ = "Clemens Horch"
__copyright__ = "Copyright 2015, Clemens Horch"
__license__ = "MIT"
__email__ = "mail@clemenshorch.de"

import re
import os
import sys

class ConAn:
	def __init__(self, label, linelength):
		self.linelength = linelength
		self.longestspeaker = ''
		self.turns = []
		self.output = ''
		self.label = label
		self.lastspeaker = ''
		self.linecount = 0

	def getbracket(self, idx):
		if idx == 0:
			return ''
		elif idx % 2 == 1:
			return '['
		else:
			return ']'

	def output_alone(self, speaker, text):
		if speaker == self.lastspeaker:
			speaker = ''
		else:
			self.lastspeaker = speaker
		self.output += '\t\\alone{' + speaker + '}{'+ text + '}\n'
		self.linecount += 1


	def output_simul(self, As, At, Bs, Bt):
		if At == '':
			self.output_alone(Bs, Bt)
		elif Bt == '':
			self.output_alone(As, At)
		else:
			if As == self.lastspeaker:
				As = ''
			else:
				self.lastspeaker = As
			self.output += '\t\simul{' + As + '}{' + At + '}{' + Bs + '}{' + Bt + '}\n'
			self.linecount += 2
			

	def append(self, txt):
		# process lines
		for line in txt.splitlines():
			if line.strip() == '':
				self.turns.append(['', ''])
				continue

			#split speaker and text
			speaker, text =  line.split(':', 1)
			speaker = speaker.strip()

			# find longest speaker name
			if len(speaker) > len(self.longestspeaker):
				self.longestspeaker = speaker

			# split into overlap groups
			text = text.strip()
			text = re.split('[\[\]]', text)

			self.turns.append([speaker, text])

	def process(self):
		textlen = self.linelength - len(self.longestspeaker) - 2

		turns_iter = enumerate(self.turns)
		for tidx, turn in turns_iter:
			# empty lines
			if turn[0] == '':
				continue

			self.lastspeaker = ''

			# no overlap
			if len(turn[1]) == 1:
				words = turn[1][0].split()
				text = ''
				while len(words) > 0:
					if len(text) + len(words[0]) > textlen:
						self.output_alone(turn[0], text)
						text = ''

					if len(words) > 0:
						text += words.pop(0) + ' '

				self.output_alone(turn[0], text)
				continue

			# overlap
			A = turn
			B = self.turns[tidx + 1]
			Ao = ''
			Bo = ''

			# loop over all overlap groups
			for i,_ in enumerate(A[1]):
				A[1][i] = self.getbracket(i) + A[1][i]
				B[1][i] = self.getbracket(i) + B[1][i]
				chunkA = A[1][i].split()
				chunkB = B[1][i].split()

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
					if len(Ao) + len(nextA) > textlen or len(Bo) + len(nextB) > textlen:
						Ao_new = ''
						Bo_new = ''
						if len(Ao) + len(nextA) > textlen and Bo != '':
							Ao += '='
							Ao_new = '= '		
						if len(Bo) + len(nextB) > textlen and Ao != '':
							Bo += '='
							Bo_new = '= '
						
						self.output_simul(A[0], Ao, B[0], Bo)				
						Ao = Ao_new
						Bo = Bo_new

					# append next word to line
					if len(chunkA) > 0:
						Ao += chunkA.pop(0) + ' '
						
					if len(chunkB) > 0:
						Bo += chunkB.pop(0) + ' '
						
			self.output_simul(A[0], Ao, B[0], Bo)	

			# skip next turn
			next(turns_iter, None)

		self.output = '\\begin{conan}[speaker=' + self.longestspeaker + ',maxline=' + str(self.linecount) + ']\n' + self.output
		if self.label:
			self.output += '\t\label{' + self.label + '}\n'
		self.output += '\end{conan}\n'

def process_file(filename, linelength):
	label = filename.replace(os.path.sep, '.')
	label = label.replace('..', '', 1)

	conan = ConAn(label, linelength)

	with open(filename, 'rb') as f:
		conan.append(f.read())

	print 'processing ' + filename
	conan.process()
	#print(conan.output)

	with open(filename + '.tex', 'wb') as f:
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

