"""HADDOCK3 scoring module."""
from os import linesep
from pathlib import Path

from haddock.gear.haddockmodel import HaddockModel
from haddock.libs.libcns import prepare_cns_input, prepare_expected_pdb
from haddock.libs.libsubprocess import CNSJob
from haddock.modules import get_engine
from haddock.modules.base_cns_module import BaseCNSModule


RECIPE_PATH = Path(__file__).resolve().parent
DEFAULT_CONFIG = Path(RECIPE_PATH, "defaults.yaml")


class HaddockModule(BaseCNSModule):
    """HADDOCK3 module to perform energy minimization scoring."""

    name = RECIPE_PATH.name

    def __init__(self, order, path, initial_params=DEFAULT_CONFIG):
        cns_script = Path(RECIPE_PATH, "cns", "emscoring.cns")
        super().__init__(order, path, initial_params, cns_script=cns_script)

    @classmethod
    def confirm_installation(cls):
        """Confirm module is installed."""
        return

    def output(self, output_fname):
        """Organize output."""
        with open(output_fname, "w") as fh:
            fh.write(f"structure\toriginal_name\tscore{linesep}")
            for pdb in self.output_models:
                # with pdb.ori_name we keep track of the original pdb
                fh.write(
                    f"{pdb.file_name}\t{pdb.ori_name}\t{pdb.score}{linesep}"
                    )
        return

    def _run(self):
        """Execute module."""
        # Pool of jobs to be executed by the CNS engine
        jobs = []

        try:
            models_to_score = self.previous_io.retrieve_models(
                individualize=True
                )
        except Exception as e:
            self.finish_with_error(e)

        self.output_models = []
        for model_num, model in enumerate(models_to_score, start=1):
            scoring_inp = prepare_cns_input(
                model_num,
                model,
                self.path,
                self.recipe_str,
                self.params,
                "emscoring",
                native_segid=True)

            scoring_out = f"emscoring_{model_num}.out"

            # create the expected PDBobject
            expected_pdb = prepare_expected_pdb(
                model, model_num, ".", "emscoring"
                )
            # fill the ori_name field of expected_pdb
            expected_pdb.ori_name = model.file_name

            self.output_models.append(expected_pdb)

            job = CNSJob(scoring_inp, scoring_out, envvars=self.envvars)

            jobs.append(job)

        # Run CNS Jobs
        self.log(f"Running CNS Jobs n={len(jobs)}")
        Engine = get_engine(self.params['mode'], self.params)
        engine = Engine(jobs)
        engine.run()
        self.log("CNS jobs have finished")

        # Get the weights from the defaults
        _weight_keys = ("w_vdw", "w_elec", "w_desolv", "w_air", "w_bsa")
        weights = {e: self.params[e] for e in _weight_keys}

        # Check for generated output, fail it not all expected files are found
        for pdb in self.output_models:
            if pdb.is_present():
                haddock_score = HaddockModel(pdb.file_name).calc_haddock_score(
                    **weights
                    )

                pdb.score = haddock_score

        output_fname = "emscoring.tsv"
        self.log(f"Saving output to {output_fname}")
        self.output(output_fname)
        
        self.export_output_models(faulty_tolerance=self.params["tolerance"])
