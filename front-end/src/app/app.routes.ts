import { Routes } from '@angular/router';
import { HomeComponent } from './pages/home/home.component';

export const routes: Routes = [
  {
    path: '',
    component: HomeComponent,
    title: 'Sofi — Feel Better'
  },
  // -------------------------------------------------------
  // ADD FUTURE ROUTES BELOW
  // -------------------------------------------------------
  {
    path: 'app',
    loadComponent: () =>
      import('./pages/upload/upload.component')
        .then(m => m.UploadComponent),
    title: 'Sofi — Upload Signal'
  },
  // -------------------------------------------------------
  {
    path: '**',
    redirectTo: ''
  }
];
