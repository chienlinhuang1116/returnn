#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
from argparse import ArgumentParser
import gzip
import xml.etree.ElementTree as etree


my_dir = os.path.dirname(os.path.abspath(__file__))
returnn_dir = os.path.dirname(my_dir)
sys.path.insert(0, returnn_dir)


class BlissItem:
  def __init__(self, segment_name, recording_filename, start_time, end_time, orth):
    """
    :param str segment_name:
    :param str recording_filename:
    :param float start_time:
    :param float end_time:
    :param str orth:
    """
    self.segment_name = segment_name
    self.recording_filename = recording_filename
    self.start_time = start_time
    self.end_time = end_time
    self.orth = orth

  def __repr__(self):
    keys = ["segment_name", "recording_filename", "start_time", "end_time", "orth"]
    return "BlissItem(%s)" % ", ".join(["%s=%r" % (key, getattr(self, key)) for key in keys])


def iter_bliss(filename):
  """
  :param str filename:
  :return: yields BlissItem
  :rtype: list[BlissItem]
  """
  corpus_file = open(filename, 'rb')
  if filename.endswith(".gz"):
    corpus_file = gzip.GzipFile(fileobj=corpus_file)

  context = iter(etree.iterparse(corpus_file, events=('start', 'end')))
  _, root = next(context) # get root element
  name_tree = [root.attrib["name"]]
  elem_tree = [root]
  count_tree = [0]
  recording_filename = None
  for event, elem in context:
    if elem.tag == "recording":
      recording_filename = elem.attrib["audio"] if event == "start" else None
    if event == 'end' and elem.tag == "segment":
      elem_orth = elem.find("orth")
      orth_raw = elem_orth.text  # should be unicode
      orth_split = orth_raw.split()
      orth = " ".join(orth_split)
      segment_name = "/".join(name_tree)
      yield BlissItem(
        segment_name=segment_name, recording_filename=recording_filename,
        start_time=float(elem.attrib["start"]), end_time=float(elem.attrib["end"]),
        orth=orth)
      root.clear()  # free memory
    if event == "start":
      count_tree[-1] += 1
      count_tree.append(0)
      elem_tree += [elem]
      elem_name = elem.attrib.get("name", None)
      if elem_name is None:
        elem_name = str(count_tree[-2])
      assert isinstance(elem_name, str)
      name_tree += [elem_name]
    elif event == "end":
      assert elem_tree[-1] is elem
      elem_tree = elem_tree[:-1]
      name_tree = name_tree[:-1]
      count_tree = count_tree[:-1]


def main():
  arg_parser = ArgumentParser()
  arg_parser.add_argument("bliss_filename")
  arg_parser.add_argument("--output_type", default="", help="e.g. segment_name")
  arg_parser.add_argument("--merge_swb_ab", action="store_true")
  arg_parser.add_argument("--sort_by_time", action="store_true")
  args = arg_parser.parse_args()
  rec_filenames = set()
  items_by_rec = {}
  for bliss_item in iter_bliss(args.bliss_filename):
    rec_name = bliss_item.recording_filename
    assert rec_name, "invalid item %r" % bliss_item
    rec_filenames.add(rec_name)
    if args.merge_swb_ab:
      rec_name = os.path.basename(rec_name)
      rec_name, _ = os.path.splitext(rec_name)
      rec_filenames.add(rec_name)
      assert rec_name[-1] in "AB"
      rec_name = rec_name[:-1]
    items_by_rec.setdefault(rec_name, []).append(bliss_item)
  if args.merge_swb_ab:
    for key in items_by_rec.keys():
      assert key + "A" in rec_filenames
      assert key + "B" in rec_filenames
  for key, ls in items_by_rec.items():
    assert isinstance(ls, list)
    if args.sort_by_time:
      ls.sort(key=lambda item: item.start_time)
    for item in ls:
      assert isinstance(item, BlissItem)
      if not args.output_type:
        print(item)
      else:
        print(getattr(item, args.output_type))


if __name__ == "__main__":
  import better_exchook
  better_exchook.install()
  main()
