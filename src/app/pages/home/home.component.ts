import { Component } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [],          // NavbarComponent removed — navbar no longer rendered
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent {

  constructor(private router: Router) {}

  /**
   * Navigates to the main application page.
   * Update the target route once the real functioning page is built.
   * See GUIDE.md → Section 6 for instructions.
   */
  onStartClick(): void {
    // TODO: Replace '/app' with the actual route path when ready
    this.router.navigate(['/app']);
  }
}
