import dedupe
import unittest
import random
import numpy
import warnings
from collections import OrderedDict

DATA_SAMPLE = (({'age': '27', 'name': 'Kyle'}, 
                {'age': '50', 'name': 'Bob'}),
               ({'age': '27', 'name': 'Kyle'}, 
                {'age': '35', 'name': 'William'}),
               ({'age': '10', 'name': 'Sue'}, 
                {'age': '35', 'name': 'William'}),
               ({'age': '27', 'name': 'Kyle'}, 
                {'age': '20', 'name': 'Jimmy'}),
               ({'age': '75', 'name': 'Charlie'}, 
                {'age': '21', 'name': 'Jimbo'}))

data_dict = OrderedDict(((0, {'name' : 'Bob',         'age' : '51'}),
                         (1, {'name' : 'Linda',       'age' : '50'}),
                         (2, {'name' : 'Gene',        'age' : '12'}),
                         (3, {'name' : 'Tina',        'age' : '15'}),
                         (4, {'name' : 'Bob B.',      'age' : '51'}),
                         (5, {'name' : 'bob belcher', 'age' : '51'}),
                         (6, {'name' : 'linda ',      'age' : '50'})))

data_dict_2 = OrderedDict(((7, {'name' : 'BOB',         'age' : '51'}),
                           (8, {'name' : 'LINDA',       'age' : '50'}),
                           (9, {'name' : 'GENE',        'age' : '12'}),
                           (10, {'name' : 'TINA',        'age' : '15'}),
                           (11, {'name' : 'BOB B.',      'age' : '51'}),
                           (12, {'name' : 'BOB BELCHER', 'age' : '51'}),
                           (13, {'name' : 'LINDA ',      'age' : '50'})))


class ActiveMatch(unittest.TestCase) :
  def setUp(self) :
    self.field_definition = [{'field' : 'name', 'type': 'String'}, 
                             {'field' :'age', 'type': 'String'}]


  def test_initialize_fields(self) :
    self.assertRaises(TypeError, dedupe.api.ActiveMatching)

    matcher = dedupe.api.ActiveMatching({},)

    assert matcher.blocker is None


  def test_check_record(self) :
    matcher = dedupe.api.ActiveMatching(self.field_definition)

    self.assertRaises(ValueError, matcher._checkRecordPairType, ())
    self.assertRaises(ValueError, matcher._checkRecordPairType, (1,2))
    self.assertRaises(ValueError, matcher._checkRecordPairType, (1,2,3))
    self.assertRaises(ValueError, matcher._checkRecordPairType, ({},{}))

    matcher._checkRecordPairType(({'name' : 'Frank', 'age' : '72'},
                                  {'name' : 'Bob', 'age' : '27'}))


  def test_add_training(self) :
    from collections import OrderedDict
    training_pairs = OrderedDict((('distinct', DATA_SAMPLE[0:3]),
                                  ('match', DATA_SAMPLE[3:5])))
    matcher = dedupe.api.ActiveMatching(self.field_definition)

    matcher._addTrainingData(training_pairs)
    numpy.testing.assert_equal(matcher.training_data['label'],
                               [b'distinct', b'distinct', b'distinct', 
                                b'match', b'match'])

    matcher._addTrainingData(training_pairs)
    numpy.testing.assert_equal(matcher.training_data['label'],
                               [b'distinct', b'distinct', b'distinct', 
                                b'match', b'match']*2)


  def test_markPair(self) :
    from collections import OrderedDict
    good_training_pairs = OrderedDict((('distinct',  DATA_SAMPLE[0:3]),
                                       ('match', DATA_SAMPLE[3:5])))
    bad_training_pairs = {'non_dupes' : DATA_SAMPLE[0:3],
                          'match' : DATA_SAMPLE[3:5]}

    matcher = dedupe.api.ActiveMatching(self.field_definition)

    self.assertRaises(ValueError, matcher.markPairs, bad_training_pairs)

    matcher.markPairs(good_training_pairs)

    numpy.testing.assert_equal(matcher.training_data['label'],
                               [b'distinct', b'distinct', b'distinct', 
                                b'match', b'match'])

    with warnings.catch_warnings(record=True) as w:
      warnings.simplefilter("always")
      matcher.markPairs({'match' : [], 'distinct' : []})
      assert len(w) == 1
      assert str(w[-1].message) == "Didn't return any labeled record pairs"

    


class DedupeTest(unittest.TestCase):
  def setUp(self) : 
    random.seed(123) 
    numpy.random.seed(456)

    field_definition = [{'field' : 'name', 'type': 'String'}, 
                        {'field' :'age', 'type': 'String'}]

    self.deduper = dedupe.Dedupe(field_definition)

  def test_blockPairs(self) :
    self.assertRaises(ValueError, self.deduper._blockedPairs, ({1:2},))
    self.assertRaises(ValueError, self.deduper._blockedPairs, ({'name':'Frank', 'age':21},))
    self.assertRaises(ValueError, self.deduper._blockedPairs, ({'1' : {'name' : 'Frank',
                                                                      'height' : 72}},))
    assert [] == list(self.deduper._blockedPairs(([('1', 
                                                    {'name' : 'Frank',
                                                     'age' : 72}, 
                                                    set([]))],)))
    assert list(self.deduper._blockedPairs(([('1', 
                                              {'name' : 'Frank',
                                               'age' : 72},
                                              set([])),
                                             ('2',
                                              {'name' : 'Bob',
                                               'age' : 27},
                                              set([]))],))) == \
                  [(('1', {'age': 72, 'name': 'Frank'}, set([])), 
                    ('2', {'age': 27, 'name': 'Bob'}, set([])))]

  def test_randomSample(self) :

    random.seed(6)
    numpy.random.seed(6)
    self.deduper.sample(data_dict, 30, 1)

    correct_result = [({'age': '50', 'name': 'Linda'}, 
                       {'age': '51', 'name': 'bob belcher'}), 
                      ({'age': '51', 'name': 'Bob'}, 
                       {'age': '51', 'name': 'Bob B.'}), 
                      ({'age': '51', 'name': 'Bob'}, 
                       {'age': '51', 'name': 'bob belcher'}), 
                      ({'age': '51', 'name': 'Bob B.'}, 
                       {'age': '51', 'name': 'bob belcher'}), 
                      ({'age': '50', 'name': 'Linda'}, 
                       {'age': '50', 'name': 'linda '})]

    for pair in correct_result:
      assert pair in self.deduper.data_sample



class LinkTest(unittest.TestCase):
  def setUp(self) : 
    random.seed(123)
    numpy.random.seed(456)

    field_definition = [{'field' : 'name', 'type': 'String'}, 
                        {'field' :'age', 'type': 'String'}]
    self.linker = dedupe.RecordLink(field_definition)

  def test_blockPairs(self) :
    self.assertRaises(ValueError, self.linker._blockedPairs, ({1:2},))
    self.assertRaises(ValueError, self.linker._blockedPairs, ({'name':'Frank', 'age':21},))
    self.assertRaises(ValueError, self.linker._blockedPairs, ({'1' : {'name' : 'Frank',
                                                                      'height' : 72}},))
    assert [] == list(self.linker._blockedPairs((([('1', 
                                                    {'name' : 'Frank',
                                                     'age' : 72}, 
                                                    set([]))],
                                                  []),)))
    assert list(self.linker._blockedPairs((([('1', {'name' : 'Frank',
                                                    'age' : 72}, set([]))],
                                            [('2', {'name' : 'Bob',
                                                    'age' : 27}, set([]))]),))) == \
                  [(('1', {'age': 72, 'name': 'Frank'}, set([])), 
                    ('2', {'age': 27, 'name': 'Bob'}, set([])))]

  def test_randomSample(self) :

    random.seed(27)
    numpy.random.seed(43)

    self.linker.sample( data_dict, data_dict_2, 50, 1)

    correct_result = [({'age': '51', 'name': 'Bob B.'}, 
                       {'age': '51', 'name': 'BOB'}), 
                      ({'age': '51', 'name': 'Bob B.'}, 
                       {'age': '51', 'name': 'BOB B.'}), 
                      ({'age': '51', 'name': 'Bob'}, 
                       {'age': '51', 'name': 'BOB B.'}), 
                      ({'age': '15', 'name': 'Tina'}, 
                       {'age': '15', 'name': 'TINA'})]

    for pair in correct_result:
      assert pair in self.linker.data_sample

    self.linker.sample(data_dict, data_dict_2, 5, 0)

    correct_result = [({'age': '51', 'name': 'Bob B.'}, 
                       {'age': '15', 'name': 'TINA'}), 
                      ({'age': '51', 'name': 'Bob B.'}, 
                       {'age': '50', 'name': 'LINDA'}), 
                      ({'age': '12', 'name': 'Gene'}, 
                       {'age': '15', 'name': 'TINA'}), 
                      ({'age': '50', 'name': 'Linda'}, 
                       {'age': '50', 'name': 'LINDA '}), 
                      ({'age': '50', 'name': 'linda '}, 
                       {'age': '51', 'name': 'BOB BELCHER'})]



if __name__ == "__main__":
    unittest.main()
