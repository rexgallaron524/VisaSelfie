# Visa Selfie progress report

September 30, 2026

The first phase of Visa Selfie is working in the local test environment. We can now follow the main journey from creating an applicant's record to receiving and reviewing their video. The next stage is to make that same experience available online and test it from a laptop and real mobile devices.

For administrators, the application provides a place to create client records, check their progress, and see which applicants still need to complete their registration or submit a recording. Each applicant receives a private registration link that the administrator can copy and send through WhatsApp. Links remain valid for 48 hours, and a replacement can be issued when needed.

For applicants, the process starts with entering their details and agreeing to the consent notice. They can then record a short video, watch it back, and retake it before submitting. The application shows a confirmation after submission and provides guidance when a link has expired or something goes wrong.

Once a video has been submitted, an administrator can watch it, download it, mark it as reviewed, or delete it. The applicant's registration and consent records remain available after video deletion. Access to recordings is restricted to authorized administrators.

We have also updated how registration links are created. The application can now use its local address during development and the correct secure website address once it is hosted online. This prepares it for sharing links with applicants on their phones. The online address still needs to be set up; the current local links only work on the computer running the application.

The main workflow has passed automated checks and a browser test covering registration, consent, video recording and submission, and administrator review. We also checked expired and replacement links. These results give us a working foundation, but we still need to confirm the experience on actual iPhones and Android phones over a secure internet connection.

The initial Phase 1 version has been saved to GitHub. The more recent improvements for online access are available in the working project but have not yet been added to the published version.

For the next stage, the planned work is:

1. **Set up an online test version.** Confirm the Windows hosting machine and arrange a secure address that can be opened from another laptop or phone. We have explored using a free Vercel address, but nothing has been deployed there yet.
2. **Complete the connection between the website and its supporting services.** Make sure signing in, opening invitations, and submitting videos all work from the online address. If we use Vercel, the upload process needs an adjustment to support larger recordings.
3. **Test the full mobile experience.** Send a registration link through WhatsApp, open it on an iPhone and an Android phone, and check camera access, recording, retakes, uploads, and confirmation messages.
4. **Check reliability and privacy online.** Confirm that recordings remain private, interrupted uploads can be retried, expired links behave correctly, and the application can recover after the hosting machine restarts.
5. **Resolve issues and prepare a demonstration.** Address anything found during testing, update the saved project, and prepare a short walkthrough of the complete applicant and administrator experience.

Appointment monitoring and bot functionality remain outside the current scope. WhatsApp messages are still sent manually, and recordings are reviewed by a person. The immediate priority is a reliable online demonstration of the registration and video collection process already working locally.
