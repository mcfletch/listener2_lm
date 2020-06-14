# Compile DeepSpeech Language Models for Dictation

This package is only required for compiling a new language model
particularly for compiling language modes which are intended for dictation
as distinct from transcription tasks.

##  Generic language model

The only significant  difference between the language models that we will generate
and the core deep speech language models  is that we will include the necessary
commands to do capitalization and other formatting.

We are also using the wikipedia corpus to produce an alternate context
which made  include more technical discussions, as the upstream  deep speech corpus
is relatively light on  technical terms.

##  Programming language model 

The programming language model is based off a free corpus of
Python programming projects' source code  and is, again,
pre processed in order to include the necessary formatting and 
capitalization  to dictate the text as observed.

Note:  Currently this corpus is  littered with many copies of
a small number of licenses/license notifications. as a result
we may wind up with a like which model that largely predicts the
LGPL  license content.

## Process for generation

We follow the [DeepSpeech LM Model Process](https://deepspeech.readthedocs.io/en/v0.7.3/Scorer.html) to produce our scorers.

## Corpora we use

* [LibreSpeech](http://www.openslr.org/resources/11/librispeech-lm-norm.txt.gz) --  the upstream deep speech corpora
* [Raw Python Code Corpus](https://figshare.com/articles/Raw_Python_Code_Corpus/11777217/1) --  a multiple gigabyte dump of python source code
* [WestburyLab.Wikipedia.Corpus](https://www.psych.ualberta.ca/~westburylab/downloads/westburylab.wikicorp.download.html) --  a dump of the content of wikipedia
* [google-10000-english.txt](https://github.com/first20hours/google-10000-english/blob/master/google-10000-english.txt) --  a list of the ten thousand most common english words
* System dictionary `/usr/share/dict/words` -- the linux system dictionary
