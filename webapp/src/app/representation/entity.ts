export enum Emotion {
  NEUTRAL,
  ANGER,
  DISGUST,
  FEAR,
  JOY,
  SADNESS,
  SURPRISE,
}

export enum Gender {
  UNDEFINED,
  FEMALE,
  MALE,
  OTHER,
}


export interface Instance {
  id: string;
}

export interface Obj extends Instance {
  label: string;
}

export interface Person extends Instance {
  name: string;
  age: number;
  gender: Gender;
}

export interface Friend extends Person {
  // no additional fields
}
