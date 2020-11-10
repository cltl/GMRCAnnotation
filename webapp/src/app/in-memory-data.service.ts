import { Injectable } from '@angular/core';
import { InMemoryDbService } from 'angular-in-memory-web-api';
import { Signal } from './scenario/scenario'
import {printLine} from "tslint/lib/verify/lines";

@Injectable({
  providedIn: 'root',
})
export class InMemoryDataService implements InMemoryDbService {
  createDb() {
    const scenario = [
      { id: 1, name: "scenario_1", start: 0, end: 100, modalities: new Map().set("image","image")}
    ];

    const image = [
      { id: 11, name: 'Dr Nice', timestamp: 0},
      { id: 12, name: 'Narco', timestamp: 0 },
      { id: 13, name: 'Bombasto', timestamp: 0 },
      { id: 14, name: 'Celeritas', timestamp: 0 },
      { id: 15, name: 'Magneta', timestamp: 0 },
      { id: 16, name: 'RubberMan', timestamp: 0 },
      { id: 17, name: 'Dynama', timestamp: 0 },
      { id: 18, name: 'Dr IQ', timestamp: 0 },
      { id: 19, name: 'Magma', timestamp: 0 },
      { id: 20, name: 'Tornado', timestamp: 0 }
    ];

    const text = [
      { id: 11, text: "Bla bla bla"}
    ];

    return {scenario, image, text};
  }
}