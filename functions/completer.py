import os
import readline
import re
from functions import data_parser

parser = data_parser.Parser()
catalog = parser.completion_data()
RE_SPACE = re.compile('.*\s+$', re.M)

class Completer(object):

    def _listdir(self, root):
        res = []
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            res.append(name)

        return res

    def _complete_path(self, path=None):
        if not path:
            return self._listdir('.')
        dirname, rest = os.path.split(path)
        tmp = dirname if dirname else '.'
        res = [os.path.join(dirname, p) for p in self._listdir(tmp) if p.startswith(rest)]

        if len(res) > 1 or not os.path.exists(path):
            return res

        if os.path.isdir(path):
            return [os.path.join(path, p) for p in self._listdir(path)]
        return [path + ' ']

    def complete_extra(self, args):
        if not args:
            return self._complete_path('.')
        return self._complete_paths(args[-1])

    def complete(self, text, state):
        buffer = readline.get_line_buffer()
        line = readline.get_line_buffer().split()

        if not line:
            return [c + ' ' for c in catalog][state]
        
        if RE_SPACE.match(buffer):
            line.append('')
        cmd = line[0].strip()
        if cmd in catalog:
            impl = getattr(self, 'complete_%s' % cmd)
            args = line[1:]
            if args:
                return (impl(args) + [None])[state]
            return [cmd + ' '][state]
        
        results = [c + ' ' for c in catalog if c.startswith(cmd)] + [None]

        return results[state]