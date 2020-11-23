import {Component, Input, OnInit} from '@angular/core';
import {SegmentComponent} from "../segment/segment.component";
import {Offset} from "../container";

@Component({
  templateUrl: './segments-offset.component.html',
  styleUrls: ['./segments-offset.component.css']
})
export class SegmentsOffsetComponent implements OnInit, SegmentComponent<Offset> {
  @Input() data: Offset;

  constructor() { }

  ngOnInit(): void {
  }
}