import {Component, OnInit} from '@angular/core';
import {ScenarioService} from '../scenario.service';
import {Scenario} from "../representation/scenario";

@Component({
  selector: 'app-scenario',
  templateUrl: './scenario.component.html',
  styleUrls: ['./scenario.component.css']
})
export class ScenarioComponent implements OnInit {
  scenarios: string[];
  selectedScenario: string;
  scenario: Scenario;

  constructor(private scenarioService: ScenarioService) { }

  ngOnInit(): void {
    this.listScenarios();
  }

  listScenarios(): void {
    this.scenarioService.listScenarios()
      .subscribe(scenarios => this.scenarios = scenarios);
  }

  loadScenario(selection: string): void {
    this.scenarioService.loadScenario(selection)
      .subscribe(scenario => this.scenario = scenario);
  }
}
