import {AfterViewInit, Component, ElementRef, Input, OnChanges, OnInit, ViewChild} from '@angular/core';
import {ImageSignal} from "../scenario";

@Component({
  selector: 'app-carousel',
  templateUrl: './carousel.component.html',
  styleUrls: ['./carousel.component.css']
})
export class CarouselComponent implements OnInit, AfterViewInit, OnChanges {
  @Input() signals: ImageSignal[];
  @Input() selected: number;

  @ViewChild('canvas', {static: false}) canvas: ElementRef;
  context: CanvasRenderingContext2D;

  constructor() { }

  ngOnInit(): void {
  }

  ngOnChanges(changes) {
    if (this.canvas) {
      this.context = this.canvas.nativeElement.getContext('2d');

      let img = new Image();
      img.onload = e => this.drawImageOnCanvas(this.context, img)
      img.src = this.signals[changes.selected.currentValue].image;
    }
  }

  ngAfterViewInit(): void {
    this.context = this.canvas.nativeElement.getContext('2d');

    let img = new Image();
    img.onload = e => this.drawImageOnCanvas(this.context, img)
    img.src = this.signals[this.selected].image;
  }

  drawImageOnCanvas(context: CanvasRenderingContext2D, image: HTMLImageElement): void {
    this.context.clearRect(0,0, this.context.canvas.width, this.context.canvas.height);

    let imgWidth = image.width;
    let imgHeight = image.height;
    let canvasWidth = this.context.canvas.width;
    let canvasHeight = this.context.canvas.height;

    let hScale = canvasWidth/imgWidth;
    let vScale = canvasHeight/imgHeight;
    let scale = Math.min(hScale, vScale);

    let scaledWidth = Math.floor(scale * imgWidth);
    let scaledHeight = Math.floor(scale * imgHeight);
    let dx = Math.floor((canvasWidth - scaledWidth) / 2);
    let dy= Math.floor((canvasHeight - scaledHeight) / 2);

    this.context.drawImage(image, dx, dy, scaledWidth, scaledHeight);
  }
}
