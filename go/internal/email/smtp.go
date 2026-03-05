package email

import (
	"crypto/tls"
	"fmt"
	"net/smtp"
	"strings"
)

type Config struct {
	Host     string
	Port     int
	User     string
	Password string
	From     string
	FromName string
}

func Send(cfg Config, to []string, subject, body string) error {
	addr := fmt.Sprintf("%s:%d", cfg.Host, cfg.Port)
	msg := buildMessage(cfg, to, subject, body)
	if cfg.Port == 465 {
		tlsConn, err := tls.Dial("tcp", addr, &tls.Config{ServerName: cfg.Host})
		if err != nil {
			return err
		}
		client, err := smtp.NewClient(tlsConn, cfg.Host)
		if err != nil {
			return err
		}
		defer client.Close()
		if err := client.Auth(smtp.PlainAuth("", cfg.User, cfg.Password, cfg.Host)); err != nil {
			return err
		}
		if err := client.Mail(cfg.From); err != nil {
			return err
		}
		for _, r := range to {
			if err := client.Rcpt(r); err != nil {
				return err
			}
		}
		w, err := client.Data()
		if err != nil {
			return err
		}
		_, err = w.Write([]byte(msg))
		if err == nil {
			err = w.Close()
		}
		return err
	}
	return smtp.SendMail(addr, smtp.PlainAuth("", cfg.User, cfg.Password, cfg.Host), cfg.From, to, []byte(msg))
}

func buildMessage(cfg Config, to []string, subject, body string) string {
	from := cfg.From
	if cfg.FromName != "" {
		from = fmt.Sprintf("%s <%s>", cfg.FromName, cfg.From)
	}
	headers := []string{
		"From: " + from,
		"To: " + strings.Join(to, ", "),
		"Subject: " + subject,
		"MIME-Version: 1.0",
		"Content-Type: text/plain; charset=UTF-8",
		"",
	}
	return strings.Join(headers, "\r\n") + body
}
