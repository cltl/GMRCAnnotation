import {Ruler} from "./representation/container";
import {ScenarioService} from "./scenario.service";
import {ContainerComponent} from "./container/container.component";
import {Type} from "@angular/core";
import {SegmentComponent} from "./segment/segment.component";
import {Annotation, Mention, Signal} from "./representation/scenario";
import {SegmentItem} from "./segment/segment-item";
import {AnnotationItem} from "./annotation/annotation-item";
import {ComponentService} from "./component.service";

function byId(obj) {
  return other => other.id === obj.id;
}

function eqId(id: string) {
  return other => other.id === id;
}

export class SignalSelection<S extends Signal<any>> {
  idx: number;
  signal: S;
  mention: Mention;
  // TODO segments + selectedSegment, same for annotations
  segment: Ruler;
  annotation: Annotation<any>;

  containerComponent: Type<ContainerComponent<any>>;
  segmentItem: SegmentItem<any>;
  annotationItem: AnnotationItem<any>;

  segments: SegmentItem<any>[];
  annotations: AnnotationItem<any>[];

  readonly scenarioId: string;
  private readonly scenarioService: ScenarioService;
  private readonly componentService: ComponentService;

  constructor(idx: number, signal: S, scenarioId: string, scenarioService: ScenarioService,
              componentService: ComponentService, init: boolean = true) {
    this.scenarioId = scenarioId;
    this.scenarioService = scenarioService;
    this.componentService = componentService;

    this.idx = idx;
    this.signal = signal;

    this.containerComponent = componentService.getContainerComponent(signal);

    if (init) {
      this.segments = this.allSegments();
      this.annotations = this.allAnnotations();
      console.log("Initialized selection");
    }
  }

  private clone() {
    let selection = new SignalSelection(this.idx, this.signal, this.scenarioId, this.scenarioService, this.componentService, false);
    selection.mention = this.mention;
    selection.segment = this.segment;
    selection.annotation = this.annotation;
    selection.containerComponent = this.containerComponent;
    selection.segmentItem = this.segmentItem;
    selection.annotationItem = this.annotationItem;
    selection.segments = this.segments;
    selection.annotations = this.annotations;

    return selection;
  }

  withMention(mention: Mention): SignalSelection<S> {
    let selection = this.clone();
    selection.mention = mention;
    selection.segment = null;
    selection.annotation = null;

    return selection;
  }

  withSegment(segment: Ruler, mentionId: string = null): SignalSelection<S> {
    let mention = (mentionId && this.signal.mentions.find(eqId(mentionId))) || this.mention;

    let selection = this.clone();
    selection.mention = mention;
    selection.segment = segment;
    selection.annotation = this.annotation;

    selection.segmentItem = segment ?
        this.segments.find(seg => seg.data === segment) :
        null;

    return selection;
  }

  // TODO AnnotationItem
  withAnnotation(annotation: Annotation<any>, mentionId: string = null): SignalSelection<S> {
    let mention = (mentionId && this.signal.mentions.find(eqId(mentionId))) || this.mention;

    let selection = this.clone();
    selection.mention = mention;
    selection.segment = this.segment;
    selection.annotation = annotation;

    selection.annotationItem = annotation ?
        this.annotations.find(ann => ann.data === annotation) :
        null;

    return selection;
  }

  addMention(select = true): Promise<SignalSelection<S>> {
    let selection = this.clone();

    return this.scenarioService.createMentionFor(this.scenarioId, this.signal)
        .then(mention => {
          selection.signal.mentions.push(mention);

          if (select) {
            selection = selection.withMention(selection.signal.mentions.slice(-1)[0]);
          }

          return selection;
        });
  }

  addAnnotation(type: string, select = true): Promise<SignalSelection<S>> {
    let selection = this.clone();

    return this.scenarioService.createAnnotationFor(this.scenarioId, this.signal, this.mention, type)
        .then(annotation => {
          let mention = selection.signal.mentions.find(byId(this.mention));
          mention.annotations.push(annotation);
          selection.annotations = selection.allAnnotations();

          if (select) {
            let newAnnotation = mention.annotations.slice(-1)[0];
            selection = selection.withAnnotation(newAnnotation);
          }

          return selection;
        });
  }

  addSegment(type = null, containerId: string = null, select = true): Promise<SignalSelection<S>> {
    let selection = this.clone();

    return this.scenarioService.createSegmentFor(this.scenarioId, this.signal, this.mention, type, containerId)
        .then(segment => {
          let mention = selection.signal.mentions.find(byId(this.mention));
          mention.segment.push(segment);
          selection.segments = selection.allSegments();

          if (select) {
            let newSegment = mention.segment.slice(-1)[0];
            selection = selection.withSegment(newSegment);
          }

          return selection;
        });
  }

  removeSegment(containerId: string): SignalSelection<S> {
    let selection = this.clone();
    selection.mention.segment = selection.mention.segment.filter(seg => seg.container_id !== containerId);
    selection.segments = selection.allSegments();

    if (selection.segment && selection.segment.container_id === containerId) {
      selection = selection.withSegment(null);
    }

    return selection;
  }

  private getSegmentComponent(segment: Ruler): Type<SegmentComponent<any>> {
    return this.componentService.getSegmentComponent(segment);
  }

  private getAnnotationComponent(annotation: Annotation<any>): Type<SegmentComponent<any>> {
    return this.componentService.getAnnotationComponent(annotation);
  }

  private allSegments(): SegmentItem<any>[] {
    return this.signal.mentions.flatMap(mention => mention.segment.map(seg => {
      return new SegmentItem(this.getSegmentComponent(seg), mention.id, seg);
    }));
  }

  private allAnnotations(): AnnotationItem<any>[] {
    return this.signal.mentions.flatMap(mention => mention.annotations.map(ann => {
      return new AnnotationItem<any>(this.getAnnotationComponent(ann), mention.id, ann);
    }));
  }
}
