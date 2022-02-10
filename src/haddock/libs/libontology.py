"""Describe the Haddock3 ontology used for communicating between modules."""
import datetime
import itertools
from enum import Enum
from os import linesep
from pathlib import Path

import jsonpickle

from haddock.core.defaults import MODULE_IO_FILE


NaN = float('nan')


class Format(Enum):
    """Input and Output possible formats."""

    PDB = "pdb"
    PDB_ENSEMBLE = "pdb"
    CNS_INPUT = "inp"
    CNS_OUTPUT = "out"
    TOPOLOGY = "psf"

    def __str__(self):
        return str(self.value)


class Persistent:
    """Any persistent file generated by this framework."""

    def __init__(self, file_name, file_type, path='.'):
        self.created = datetime.datetime.now().isoformat(' ', 'seconds')
        self.file_name = Path(file_name).name
        self.file_type = file_type
        self.path = str(Path(path).resolve())
        self.full_name = str(Path(path, self.file_name))
        self.rel_path = Path('..', Path(self.path).name, file_name)

    def __repr__(self):
        rep = (f"[{self.file_type}|{self.created}] "
               f"{Path(self.path) / self.file_name}")
        return rep

    def is_present(self):
        """Check if the persisent file exists on disk."""
        return self.rel_path.resolve().exists()


class PDBFile(Persistent):
    """Represent a PDB file."""

    def __init__(self, file_name, topology=None, path='.', score=NaN):
        super().__init__(file_name, Format.PDB, path)
        self.topology = topology
        self.score = score
        self.ori_name = None
        self.clt_id = None
        self.clt_rank = None
        self.clt_model_rank = None
        self.len = score

    def __lt__(self, other):
        return self.score < other.score

    def __gt__(self, other):
        return self.score > other.score

    def __eq__(self, other):
        return self.score == other.score

    def __hash__(self):
        return id(self)


class TopologyFile(Persistent):
    """Represent a CNS-generated topology file."""

    def __init__(self, file_name, path='.'):
        super().__init__(file_name, Format.TOPOLOGY, path)


class ModuleIO:
    """Intercommunicating modules and exchange input/output information."""

    def __init__(self):
        self.input = []
        self.output = []

    def add(self, persistent, mode="i"):
        """Add a given filename as input or output."""
        if mode == "i":
            if isinstance(persistent, list):
                self.input.extend(persistent)
            else:
                self.input.append(persistent)
        else:
            if isinstance(persistent, list):
                self.output.extend(persistent)
            else:
                self.output.append(persistent)

    def save(self, path=".", filename=MODULE_IO_FILE):
        """Save Input/Output needed files by this module to disk."""
        fpath = Path(path, filename)
        with open(fpath, "w") as output_handler:
            to_save = {"input": self.input,
                       "output": self.output}
            jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
            output_handler.write(jsonpickle.encode(to_save))
        return fpath

    def load(self, filename):
        """Load the content of a given IO filename."""
        with open(filename) as json_file:
            content = jsonpickle.decode(json_file.read())
            self.input = content["input"]
            self.output = content["output"]

    def retrieve_models(self, crossdock=False, individualize=False):
        """Retrieve the PDBobjects to be used in the module."""
        # Get the models generated in previous step
        model_list = []
        input_dic = {}

        for i, element in enumerate(self.output):
            if isinstance(element, dict):
                position_list = input_dic.setdefault(i, [])
                for key in element:
                    position_list.append(element[key])

            elif element.file_type == Format.PDB:
                model_list.append(element)

        if input_dic and not crossdock and not individualize:
            # check if all ensembles contain the same number of models
            sub_lists = iter(input_dic.values())
            _len = len(next(sub_lists))
            if not all(len(sub) == _len for sub in sub_lists):
                _msg = ("Different number of models in molecules,"
                        " cannot prepare pairwise complexes.")
                raise Exception(_msg)

            # prepare pairwise combinations
            model_list = [values for values in zip(*input_dic.values())]
        elif input_dic and crossdock and not individualize:
            model_list = [
                values for values in itertools.product(*input_dic.values())
                ]
        elif input_dic and individualize:
            model_list = list(itertools.chain(*input_dic.values()))

        return model_list

    def check_faulty(self):
        """Check how many of the output exists."""
        total = 0.0
        present = 0.0
        for element in self.output:
            if isinstance(element, dict):
                total += len(element.values())
                present += sum(j.is_present() for j in element.values())
            else:
                total += 1
                if element.is_present():
                    present += 1

        if total == 0:
            _msg = ("No expected output was passed to ModuleIO")
            raise Exception(_msg)

        faulty_per = (1 - (present / total)) * 100

        # added this method here to avoid modifying all calls in the
        # modules' run method. We can think about restructure this part
        # in the future.
        self.remove_missing()

        return faulty_per

    def remove_missing(self):
        """Remove missing structure from `output`."""
        # can't modify a list/dictionary within a loop
        idxs = []
        for idx, element in enumerate(self.output):
            if isinstance(element, dict):
                for key2 in list(element.keys()):
                    if not element[key2].is_present():
                        element.pop(key2)
            else:
                if not element.is_present():
                    idxs.append(idx)

        for idx in idxs:
            self.output.pop(idx)

    def __repr__(self):
        return f"Input: {self.input}{linesep}Output: {self.output}"
