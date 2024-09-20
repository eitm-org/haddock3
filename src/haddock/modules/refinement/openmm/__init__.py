"""OpenMM refinement module for HADDOCK3."""
import os
import shutil

from contextlib import suppress
from pathlib import Path
from subprocess import run as subprocrun
from haddock.core.exceptions import ThirdPartyIntallationError, HaddockModuleError
from haddock.libs.libontology import PDBFile
from haddock.modules import BaseHaddockModule, get_engine

# allow general testing when OpenMM is not installed
with suppress(ImportError):
    from haddock.modules.refinement.openmm.openmm import OPENMM


RECIPE_PATH = Path(__file__).resolve().parent
DEFAULT_CONFIG = Path(RECIPE_PATH, "defaults.yaml")


class HaddockModule(BaseHaddockModule):
    """HADDOCK3 OpenMM module."""

    name = RECIPE_PATH.name

    def __init__(self, order, path, initial_params=DEFAULT_CONFIG):
        super().__init__(order, path, initial_params)

    def create_directories(self) -> dict[str, str]:
        """Create the necessary directories and provides the paths."""
        directory_list = [
            "pdbfixer",
            "solvation_boxes",
            "intermediates",
            "md_raw_output",
            "openmm_output",
            "simulation_stats"
            ]

        directory_dict = {}
        for dir in directory_list:
            self.log(f"Creating directory {dir}")
            os.mkdir(dir)
            directory_dict[dir] = dir
        
        return directory_dict
    
    def remove_directories(self) -> None:
        """Remove unnecessary directories full of heavy files."""
        directory_list = [
            "pdbfixer",
            "md_raw_output",
            "solvation_boxes",
            ]
        for dir in directory_list:
            self.log(f"Removing temporary directory {dir}")
            shutil.rmtree(dir)
        return None

    @classmethod
    def confirm_installation(cls) -> None:
        """Confirm installation of openmm and pdfixer.

        Raises
        ------
        ThirdPartyIntallationError
            When OpenMM is not installed
        ThirdPartyIntallationError
            When OpenMM pdbfixer is not installed
        """
        def run_subprocess(command_to_run: str) -> str:
            """Run subprocess."""
            subprocess_output = subprocrun(
                [command_to_run],
                shell=True,
                capture_output=True,
                encoding='utf-8',
                )
            return subprocess_output.stdout.strip()

        checkOpenMM = run_subprocess("conda list openmm --json")
        checkPdbfixer = run_subprocess("conda list pdbfixer --json")

        if (checkOpenMM == "[]"):
            raise ThirdPartyIntallationError(
                "OpenMM is not installed in conda."
                )
        if (checkPdbfixer == "[]"):
            raise ThirdPartyIntallationError(
                "OpenMM pdbfixer is not installed in conda."
                )
        return None

    def _run(self) -> None:
        """Execute module."""
        # Retrieve previous models
        previous_models = self.previous_io.retrieve_models(
            individualize=True
            )
        previous_models.sort()

        # create directories
        directory_dict = self.create_directories()

        # Build list of OPENMM jobs
        openmm_jobs: list[OPENMM] = []
        for i, model_to_be_simulated in enumerate(previous_models, start=1):
            # Create a openmm job
            openmm_job_i = OPENMM(
                i,
                model_to_be_simulated,
                Path("."),
                directory_dict,
                self.params,
                )
            # Hold it
            openmm_jobs.append(openmm_job_i)

        # running jobs
        scheduling_engine = get_engine(self.params["mode"], self.params)
        scheduler = scheduling_engine(openmm_jobs)
        scheduler.run()

        # self.log('Creating output ensemble...')
        # export models
        output_pdbs = list(Path(directory_dict["openmm_output"]).glob("*.pdb"))

        # Check if at least one output file was generated
        if len(output_pdbs) == 0:
            raise HaddockModuleError(
                "No output models generated. Check Openmm Execution."
                )

        # deleting unnecessary directories
        self.log("Removing unnecessary directories...")
        self.remove_directories()

        self.log("Completed OpenMM module run.")
        self.log(
            "If you want to continue the haddock3 workflow after"
            " the OpenMM module, the next module should be `[topoaa]`, "
            "to rebuild the CNS molecular topologies."
            )
        
        # Setting the output variable
        self.output_models = [
            PDBFile(openmmout)
            for openmmout in sorted(output_pdbs)
            ]
        # Generating standardized haddock3 outputs
        self.export_io_models()
